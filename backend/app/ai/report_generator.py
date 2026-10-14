"""
Automated Investigation Report generator.

Takes a cluster of related audit-log entries + alerts for an incident and
produces a structured report (dict) that the /reports router can render
to PDF via reportlab. Keeps the "LLM for forensic report generation" role
as a plain-language summarizer over facts we already trust (the AI never
invents timeline events -- it only narrates ones already in the audit log).
"""
from datetime import datetime
from typing import Any


def build_incident_report(
    incident_id: str,
    logs: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    paper: dict[str, Any] | None = None,
) -> dict[str, Any]:
    users_involved = sorted({log["user_name"] for log in logs})
    highest_alert = max(alerts, key=lambda a: a["risk_score"], default=None)

    timeline = [
        {
            "timestamp": log["timestamp"],
            "actor": log["user_name"],
            "action": log["action"],
            "status": log["status"],
            "ip_address": log["ip_address"],
            "device": log["device"],
        }
        for log in sorted(logs, key=lambda l: l["timestamp"])
    ]

    summary = (
        f"Incident {incident_id} involved {len(users_involved)} user(s) across "
        f"{len(logs)} recorded action(s)."
    )
    if paper:
        summary += f" The incident concerns question paper '{paper.get('title')}' ({paper.get('subject')})."
    if highest_alert:
        summary += (
            f" Peak assessed risk level was {highest_alert['risk_level']} "
            f"(score {highest_alert['risk_score']}/100, confidence {highest_alert['confidence']})."
        )

    return {
        "incident_id": incident_id,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": summary,
        "timeline": timeline,
        "users_involved": users_involved,
        "affected_paper": paper,
        "risk_level": highest_alert["risk_level"] if highest_alert else "Low",
        "contributing_factors": highest_alert["reasons"] if highest_alert else [],
        "recommended_action": highest_alert["recommended_action"] if highest_alert else "No action required.",
    }
