from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import database
from app.models.user import Role, UserOut
from app.security.auth_utils import require_roles
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
async def list_users(user: dict = Depends(require_roles("administrator"))):
    cursor = database.users.find()
    return [UserOut(**doc) async for doc in cursor]


class RoleUpdate(BaseModel):
    role: Role


@router.patch("/{user_id}/role", response_model=UserOut)
async def update_role(user_id: str, payload: RoleUpdate, admin: dict = Depends(require_roles("administrator"))):
    target = await database.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")

    if payload.role == "administrator" and target["role"] != "administrator":
        existing_admin = await database.users.find_one(
            {"role": "administrator", "id": {"$ne": user_id}}
        )
        if existing_admin:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{existing_admin['name']} is already the Administrator. Only one is "
                    "allowed at a time -- demote them to another role first, then promote "
                    f"{target['name']}."
                ),
            )

    await database.users.update_one({"id": user_id}, {"$set": {"role": payload.role}})
    await record_audit_log(
        user_id=admin["sub"], user_name=admin["name"], role=admin["role"],
        ip_address="internal", device="api", action="UPDATE_USER_ROLE",
        status="SUCCESS", permission_escalation=True,
    )
    updated = await database.users.find_one({"id": user_id})
    return UserOut(**updated)


@router.patch("/{user_id}/status", response_model=UserOut)
async def toggle_status(user_id: str, is_active: bool, admin: dict = Depends(require_roles("administrator"))):
    target = await database.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")

    if user_id == admin["sub"] and not is_active:
        raise HTTPException(status_code=400, detail="You cannot suspend your own administrator account.")

    await database.users.update_one({"id": user_id}, {"$set": {"is_active": is_active}})
    action = "ACTIVATE_USER" if is_active else "SUSPEND_USER"
    await record_audit_log(
        user_id=admin["sub"], user_name=admin["name"], role=admin["role"],
        ip_address="internal", device="api", action=action,
        status="SUCCESS",
    )
    updated = await database.users.find_one({"id": user_id})
    return UserOut(**updated)


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_roles("administrator"))):
    target = await database.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")

    if target["role"] == "administrator":
        raise HTTPException(
            status_code=400,
            detail="Can't delete the Administrator account. Demote to another role first if you need to remove it.",
        )
    if user_id == admin["sub"]:
        raise HTTPException(status_code=400, detail="You can't delete your own account.")

    await database.users.delete_one({"id": user_id})
    await record_audit_log(
        user_id=admin["sub"], user_name=admin["name"], role=admin["role"],
        ip_address="internal", device="api", action="DELETE_USER", status="SUCCESS",
    )
    return {"detail": f"{target['name']} ({target['email']}) has been removed."}
