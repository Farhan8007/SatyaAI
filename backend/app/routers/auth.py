from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Request

from app.database import database
from app.models.user import UserCreate, UserLogin, UserOut
from app.security.auth_utils import create_access_token, hash_password, verify_password
from app.services.audit_service import record_audit_log
from app.services.email_service import send_invite_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut)
async def signup(payload: UserCreate):
    existing = await database.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if payload.role == "administrator":
        existing_admin = await database.users.find_one({"role": "administrator"})
        if existing_admin:
            raise HTTPException(
                status_code=400,
                detail=(
                    "This system already has an Administrator "
                    f"({existing_admin['name']}). Only one is allowed at a time -- "
                    "ask them to invite you with a different role, or to demote/transfer "
                    "the Administrator role first."
                ),
            )

    verification_token = str(uuid.uuid4())
    user_doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": payload.email,
        "role": payload.role,
        "institution": payload.institution,
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.utcnow(),
        "last_login": None,
        "is_active": True,
        "failed_login_count": 0,
        "known_devices": [],
        "known_ips": [],
        "email_verified": False,
        "verification_token": verification_token,
    }

    email_sent = send_invite_email(payload.email, payload.name, payload.role, payload.password, verification_token)

    # If email sending isn't configured at all, we have no way to verify
    # anyone's address -- don't lock the whole app out, just skip the
    # requirement. Once SMTP is configured, every new signup genuinely
    # has to click the link before they can log in.
    if not email_sent:
        user_doc["email_verified"] = True
        user_doc["verification_token"] = None

    await database.users.insert_one(user_doc)
    return UserOut(**user_doc)


@router.get("/verify-email")
async def verify_email(token: str):
    user = await database.users.find_one({"verification_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="This verification link is invalid or has already been used.")

    await database.users.update_one(
        {"id": user["id"]},
        {"$set": {"email_verified": True, "verification_token": None}},
    )
    return {"detail": "Email verified. You can now sign in."}


@router.post("/login")
async def login(payload: UserLogin, request: Request):
    user = await database.users.find_one({"email": payload.email})
    ip = request.client.host if request.client else "unknown"
    device = request.headers.get("user-agent", "unknown")

    if not user or not verify_password(payload.password, user["hashed_password"]):
        if user:
            await database.users.update_one(
                {"id": user["id"]}, {"$inc": {"failed_login_count": 1}}
            )
            await record_audit_log(
                user_id=user["id"], user_name=user["name"], role=user["role"],
                ip_address=ip, device=device, action="LOGIN", status="FAILED",
            )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("is_active", True):
        await record_audit_log(
            user_id=user["id"], user_name=user["name"], role=user["role"],
            ip_address=ip, device=device, action="LOGIN", status="FAILED",
        )
        raise HTTPException(
            status_code=403,
            detail="This account has been suspended. Contact your Administrator for access.",
        )

    if not user.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before signing in -- check your inbox for the verification link.",
        )

    is_new_device = device not in user.get("known_devices", [])
    is_new_ip = ip not in user.get("known_ips", [])

    await database.users.update_one(
        {"id": user["id"]},
        {
            "$set": {"last_login": datetime.utcnow(), "failed_login_count": 0},
            "$addToSet": {"known_devices": device, "known_ips": ip},
        },
    )

    await record_audit_log(
        user_id=user["id"], user_name=user["name"], role=user["role"],
        ip_address=ip, device=device, action="LOGIN", status="SUCCESS",
        is_new_device=is_new_device, is_new_ip=is_new_ip,
    )

    token = create_access_token({"sub": user["id"], "role": user["role"], "name": user["name"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "name": user["name"]}
