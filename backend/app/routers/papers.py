import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from app.database import database
from app.models.paper import ApprovalStatus, PaperOut
from app.security.auth_utils import get_current_user, require_roles
from app.security.encryption import aes_encrypt, sha256_hash, sign_data
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("/upload", response_model=PaperOut)
async def upload_paper(
    title: str = Form(...),
    subject: str = Form(...),
    exam_date: datetime = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("paper_setter", "administrator")),
):
    content = await file.read()
    file_hash = sha256_hash(content)
    signature = sign_data(content)
    encrypted_blob = aes_encrypt(content)

    doc = {
        "id": str(uuid.uuid4()),
        "title": title,
        "subject": subject,
        "exam_date": exam_date,
        "exam_centre": None,
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
        ip_address="internal", device="api", action="UPLOAD_PAPER",
        status="SUCCESS", paper_id=doc["id"],
    )
    return PaperOut(**doc)


@router.get("/", response_model=list[PaperOut])
async def list_papers(user: dict = Depends(get_current_user)):
    cursor = database.papers.find()
    papers = [PaperOut(**p) async for p in cursor]
    return papers


@router.post("/{paper_id}/approve", response_model=PaperOut)
async def approve_paper(
    paper_id: str,
    remarks: str = "",
    user: dict = Depends(require_roles("moderator", "administrator")),
):
    paper = await database.papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(404, "Paper not found")

    await database.papers.update_one(
        {"id": paper_id},
        {"$set": {"status": ApprovalStatus.approved, "remarks": remarks}},
    )
    await record_audit_log(
        user_id=user["sub"], user_name=user["name"], role=user["role"],
        ip_address="internal", device="api", action="APPROVE_PAPER",
        status="SUCCESS", paper_id=paper_id,
    )
    updated = await database.papers.find_one({"id": paper_id})
    return PaperOut(**updated)


@router.post("/{paper_id}/reject", response_model=PaperOut)
async def reject_paper(
    paper_id: str,
    remarks: str = "",
    user: dict = Depends(require_roles("moderator", "administrator")),
):
    paper = await database.papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(404, "Paper not found")

    await database.papers.update_one(
        {"id": paper_id},
        {"$set": {"status": ApprovalStatus.rejected, "remarks": remarks}},
    )
    await record_audit_log(
        user_id=user["sub"], user_name=user["name"], role=user["role"],
        ip_address="internal", device="api", action="REJECT_PAPER",
        status="SUCCESS", paper_id=paper_id,
    )
    updated = await database.papers.find_one({"id": paper_id})
    return PaperOut(**updated)


@router.post("/{paper_id}/unlock")
async def unlock_paper(
    paper_id: str,
    user: dict = Depends(require_roles("examination_centre", "administrator")),
):
    """Timed unlock: exam centre can only decrypt after status == approved."""
    paper = await database.papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(404, "Paper not found")
    if paper["status"] != ApprovalStatus.approved:
        raise HTTPException(403, "Paper has not completed the approval workflow")

    await record_audit_log(
        user_id=user["sub"], user_name=user["name"], role=user["role"],
        ip_address="internal", device="api", action="UNLOCK_PAPER",
        status="SUCCESS", paper_id=paper_id,
    )
    return {"detail": "Paper unlocked for secure download.", "sha256_hash": paper["sha256_hash"]}
