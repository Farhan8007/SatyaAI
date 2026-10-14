from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from app.database import database
from app.security.auth_utils import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary(user: dict = Depends(get_current_user)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_papers = await database.papers.count_documents({})
    pending_approvals = await database.papers.count_documents({"status": "pending"})
    todays_logins = await database.audit_logs.count_documents(
        {"action": "LOGIN", "status": "SUCCESS", "timestamp": {"$gte": today_start}}
    )
    failed_logins_today = await database.audit_logs.count_documents(
        {"action": "LOGIN", "status": "FAILED", "timestamp": {"$gte": today_start}}
    )
    open_alerts = await database.alerts.count_documents({"resolved": False})

    high_risk_alerts = database.alerts.find({"resolved": False}).sort("risk_score", -1).limit(5)
    recent_alerts = [a async for a in high_risk_alerts]

    avg_risk_cursor = database.alerts.aggregate([
        {"$match": {"resolved": False}},
        {"$group": {"_id": None, "avg_risk": {"$avg": "$risk_score"}}},
    ])
    avg_risk_result = [doc async for doc in avg_risk_cursor]
    overall_risk_score = round(avg_risk_result[0]["avg_risk"], 1) if avg_risk_result else 0.0

    recent_timeline = database.audit_logs.find().sort("timestamp", -1).limit(15)
    timeline = [t async for t in recent_timeline]

    return {
        "total_papers": total_papers,
        "pending_approvals": pending_approvals,
        "todays_logins": todays_logins,
        "failed_logins_today": failed_logins_today,
        "open_alerts": open_alerts,
        "overall_risk_score": overall_risk_score,
        "recent_alerts": [
            {
                "id": a["id"], "user_name": a["user_name"], "risk_level": a["risk_level"],
                "risk_score": a["risk_score"], "reasons": a["reasons"],
            }
            for a in recent_alerts
        ],
        "activity_timeline": [
            {
                "timestamp": t["timestamp"], "user_name": t["user_name"],
                "action": t["action"], "status": t["status"],
            }
            for t in timeline
        ],
    }
