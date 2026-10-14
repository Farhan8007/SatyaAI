import io
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.database import database
from app.models.paper import ApprovalStatus, PaperOut
from app.security.auth_utils import get_current_user, require_roles, verify_paper_access
from app.security.encryption import aes_encrypt, aes_decrypt, sha256_hash, sign_data, verify_signature
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("/upload", response_model=PaperOut)
async def upload_paper(
    title: str = Form(...),
    subject: str = Form(...),
    exam_date: datetime = Form(...),
    exam_centre: Optional[str] = Form(None),
    unlock_window_minutes: Optional[int] = Form(None),
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("paper_setter", "administrator")),
    request: Request = None,
):
    ip = request.client.host if request and request.client else "internal"
    device = request.headers.get("user-agent", "api") if request else "api"

    content = await file.read()
    file_hash = sha256_hash(content)
    signature = sign_data(content)
    encrypted_blob = aes_encrypt(content)

    doc = {
        "id": str(uuid.uuid4()),
        "title": title,
        "subject": subject,
        "exam_date": exam_date,
        "exam_centre": exam_centre,
        "unlock_window_minutes": unlock_window_minutes or settings.unlock_window_minutes,
        "setter_id": user["sub"],
        "setter_name": user["name"],
        "status": ApprovalStatus.pending,
        "sha256_hash": file_hash,
        "signature": signature,
        "is_encrypted": True,
        "unlock_time": None,
        "created_at": datetime.utcnow(),
        "remarks": None,
        "encrypted_blob": encrypted_blob,
    }
    await database.papers.insert_one(doc)

    await record_audit_log(
        user_id=user["sub"], user_name=user["name"], role=user["role"],
        ip_address=ip, device=device, action="UPLOAD_PAPER",
        status="SUCCESS", paper_id=doc["id"],
    )
    return PaperOut(**doc)


@router.get("/", response_model=list[PaperOut])
async def list_papers(user: dict = Depends(get_current_user)):
    role = user.get("role")
    uid = user.get("sub")

    if role == "paper_setter":
        cursor = database.papers.find({"setter_id": uid})
    elif role == "examination_centre":
        allowed_centres = {uid}
        if user.get("institution"):
            allowed_centres.add(user["institution"])
        if user.get("name"):
            allowed_centres.add(user["name"])
        cursor = database.papers.find({
            "$or": [
                {"exam_centre": {"$in": list(allowed_centres)}},
                {"exam_centre": None},
            ]
        })
    else:
        # administrators, moderators, security auditors can view all papers
        cursor = database.papers.find()

    papers = [PaperOut(**p) async for p in cursor]
    return papers


@router.post("/{paper_id}/approve", response_model=PaperOut)
async def approve_paper(
    paper_id: str,
    remarks: str = "",
    user: dict = Depends(require_roles("moderator", "administrator")),
    request: Request = None,
):
    ip = request.client.host if request and request.client else "internal"
    device = request.headers.get("user-agent", "api") if request else "api"

    paper = await database.papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(404, "Paper not found")

    await database.papers.update_one(
        {"id": paper_id},
        {"$set": {"status": ApprovalStatus.approved, "remarks": remarks}},
    )
    await record_audit_log(
        user_id=user["sub"], user_name=user["name"], role=user["role"],
        ip_address=ip, device=device, action="APPROVE_PAPER",
        status="SUCCESS", paper_id=paper_id,
    )
    updated = await database.papers.find_one({"id": paper_id})
    return PaperOut(**updated)


@router.post("/{paper_id}/reject", response_model=PaperOut)
async def reject_paper(
    paper_id: str,
    remarks: str = "",
    user: dict = Depends(require_roles("moderator", "administrator")),
    request: Request = None,
):
    ip = request.client.host if request and request.client else "internal"
    device = request.headers.get("user-agent", "api") if request else "api"

    paper = await database.papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(404, "Paper not found")

    await database.papers.update_one(
        {"id": paper_id},
        {"$set": {"status": ApprovalStatus.rejected, "remarks": remarks}},
    )
    await record_audit_log(
        user_id=user["sub"], user_name=user["name"], role=user["role"],
        ip_address=ip, device=device, action="REJECT_PAPER",
        status="SUCCESS", paper_id=paper_id,
    )
    updated = await database.papers.find_one({"id": paper_id})
    return PaperOut(**updated)


@router.post("/{paper_id}/unlock")
async def unlock_paper(
    paper_id: str,
    user: dict = Depends(require_roles("examination_centre", "administrator")),
    request: Request = None,
):
    """Timed unlock: exam centre can only decrypt after status == approved."""
    ip = request.client.host if request and request.client else "internal"
    device = request.headers.get("user-agent", "api") if request else "api"

    paper = await database.papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(404, "Paper not found")

    await verify_paper_access(user, paper)

    if paper["status"] != ApprovalStatus.approved:
        raise HTTPException(403, "Paper has not completed the approval workflow")

    # Day 5 Release-Window Enforcement: reject unlock if now < (exam_date - unlock_window)
    exam_date = paper.get("exam_date")
    if exam_date:
        if isinstance(exam_date, str):
            exam_date = datetime.fromisoformat(exam_date.replace("Z", "+00:00"))

        now_utc = datetime.now(timezone.utc)
        target_exam_date = exam_date if exam_date.tzinfo else exam_date.replace(tzinfo=timezone.utc)
        unlock_window = timedelta(minutes=paper.get("unlock_window_minutes") or settings.unlock_window_minutes)
        earliest_unlock = target_exam_date - unlock_window

        if now_utc < earliest_unlock:
            await record_audit_log(
                user_id=user["sub"], user_name=user["name"], role=user["role"],
                ip_address=ip, device=device, action="PREMATURE_UNLOCK_ATTEMPT",
                status="FAILED", paper_id=paper_id,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Exam release window not open yet. Unlocks allowed starting {earliest_unlock.isoformat()}.",
            )

    now = datetime.utcnow()
    await database.papers.update_one(
        {"id": paper_id},
        {"$set": {"unlock_time": now}},
    )

    await record_audit_log(
        user_id=user["sub"], user_name=user["name"], role=user["role"],
        ip_address=ip, device=device, action="UNLOCK_PAPER",
        status="SUCCESS", paper_id=paper_id,
    )
    return {"detail": "Paper unlocked for secure download.", "sha256_hash": paper["sha256_hash"]}


@router.get("/{paper_id}/download")
async def download_paper(
    paper_id: str,
    user: dict = Depends(require_roles("examination_centre", "administrator")),
    request: Request = None,
):
    """Secure paper download: decrypts ciphertext, validates SHA-256 and RSA-PSS signature,

    and streams verified bytes to the authorized examination centre or administrator.
    """
    ip = request.client.host if request and request.client else "internal"
    device = request.headers.get("user-agent", "api") if request else "api"

    paper = await database.papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(404, "Paper not found")

    # Centre & role scoping check
    await verify_paper_access(user, paper)

    # Workflow state check: must be approved
    if paper.get("status") != ApprovalStatus.approved:
        raise HTTPException(403, "Paper has not been approved for download")

    # Unlock check: must have been unlocked
    if not paper.get("unlock_time"):
        raise HTTPException(403, "Paper must be unlocked before download")

    encrypted_blob = paper.get("encrypted_blob")
    if not encrypted_blob:
        raise HTTPException(404, "Encrypted paper payload not found")

    # 1. AES Decrypt
    try:
        decrypted_bytes = aes_decrypt(encrypted_blob)
    except Exception:
        await record_audit_log(
            user_id=user["sub"], user_name=user["name"], role=user["role"],
            ip_address=ip, device=device, action="TAMPER_DETECTED",
            status="FAILED", paper_id=paper_id,
        )
        raise HTTPException(409, "Decryption failed: paper content corrupted or tampered")

    # 2. SHA-256 Hash Integrity Verification
    computed_hash = sha256_hash(decrypted_bytes)
    if computed_hash != paper.get("sha256_hash"):
        await record_audit_log(
            user_id=user["sub"], user_name=user["name"], role=user["role"],
            ip_address=ip, device=device, action="TAMPER_DETECTED",
            status="FAILED", paper_id=paper_id,
        )
        raise HTTPException(409, "Integrity verification failed: paper hash mismatch")

    # 3. RSA-PSS Digital Signature Verification
    signature = paper.get("signature")
    if not signature or not verify_signature(decrypted_bytes, signature):
        await record_audit_log(
            user_id=user["sub"], user_name=user["name"], role=user["role"],
            ip_address=ip, device=device, action="TAMPER_DETECTED",
            status="FAILED", paper_id=paper_id,
        )
        raise HTTPException(409, "Authenticity verification failed: invalid digital signature")

    # 4. Success Audit Log
    await record_audit_log(
        user_id=user["sub"], user_name=user["name"], role=user["role"],
        ip_address=ip, device=device, action="DOWNLOAD_PAPER",
        status="SUCCESS", paper_id=paper_id,
    )

    filename = f"{paper.get('title', 'question_paper').replace(' ', '_')}.pdf"
    return StreamingResponse(
        io.BytesIO(decrypted_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
