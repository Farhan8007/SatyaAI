from fastapi import APIRouter, Depends, Query

from app.database import database
from app.models.audit_log import AuditLogEntry
from app.security.auth_utils import get_current_user
from app.services.audit_service import verify_chain_integrity

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("/", response_model=list[AuditLogEntry])
async def list_audit_logs(
    limit: int = Query(100, le=1000),
    user_id: str | None = None,
    action: str | None = None,
    user: dict = Depends(get_current_user),
):
    query: dict = {}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action

    cursor = database.audit_logs.find(query).sort("timestamp", -1).limit(limit)
    logs = [AuditLogEntry(**doc) async for doc in cursor]
    return logs


@router.get("/verify-integrity")
async def verify_integrity(user: dict = Depends(get_current_user)):
    cursor = database.audit_logs.find()
    logs = [doc async for doc in cursor]
    intact = verify_chain_integrity(logs)
    return {"intact": intact, "entries_checked": len(logs)}
