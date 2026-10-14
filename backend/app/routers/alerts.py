from fastapi import APIRouter, Depends, HTTPException

from app.database import database
from app.models.alert import Alert
from app.security.auth_utils import get_current_user, require_roles

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/", response_model=list[Alert])
async def list_alerts(resolved: bool | None = None, user: dict = Depends(get_current_user)):
    query: dict = {}
    if resolved is not None:
        query["resolved"] = resolved
    cursor = database.alerts.find(query).sort("created_at", -1)
    return [Alert(**doc) async for doc in cursor]


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: str, user: dict = Depends(require_roles("security_auditor", "administrator"))):
    result = await database.alerts.update_one({"id": alert_id}, {"$set": {"resolved": True}})
    if result.matched_count == 0:
        raise HTTPException(404, "Alert not found")
    return {"detail": "Alert marked as resolved"}
