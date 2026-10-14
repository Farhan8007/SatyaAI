import io
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.database import database
from app.security.auth_utils import require_roles
from app.ai.report_generator import build_incident_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/incident/{alert_id}")
async def generate_incident_report(
    alert_id: str,
    user: dict = Depends(require_roles("security_auditor", "administrator")),
):
    alert = await database.alerts.find_one({"id": alert_id})
    if not alert:
        raise HTTPException(404, "Alert not found")

    logs = [
        doc async for doc in database.audit_logs.find({"id": {"$in": alert["related_log_ids"]}})
    ] or [doc async for doc in database.audit_logs.find({"user_id": alert["user_id"]}).limit(20)]

    paper = None
    if alert.get("related_paper_id"):
        paper = await database.papers.find_one({"id": alert["related_paper_id"]})

    report = build_incident_report(
        incident_id=str(uuid.uuid4())[:8].upper(),
        logs=logs,
        alerts=[alert],
        paper=paper,
    )
    await database.reports.insert_one(report.copy())
    return report


@router.get("/incident/{incident_id}")
async def get_incident_report(
    incident_id: str,
    user: dict = Depends(require_roles("security_auditor", "administrator")),
):
    report = await database.reports.find_one({"incident_id": incident_id}, {"_id": 0})
    if not report:
        raise HTTPException(404, "Report not found")
    return report


@router.get("/")
async def list_reports(user: dict = Depends(require_roles("security_auditor", "administrator"))):
    cursor = database.reports.find({}, {"_id": 0}).sort("generated_at", -1)
    return [doc async for doc in cursor]


@router.get("/incident/{incident_id}/pdf")
async def download_incident_pdf(incident_id: str, user: dict = Depends(require_roles("security_auditor", "administrator"))):
    report = await database.reports.find_one({"incident_id": incident_id})
    if not report:
        raise HTTPException(404, "Report not found")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - inch

    def line(text: str, size: int = 11, gap: int = 18, bold: bool = False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(inch, y, text)
        y -= gap

    line(f"SATYA AI - Investigation Report", 16, 26, bold=True)
    line(f"Incident ID: {report['incident_id']}", 11, 20)
    line(f"Generated: {report['generated_at']}", 10, 24)
    line("Summary", 13, 18, bold=True)
    line(report["summary"][:110], 10, 14)
    line(f"Risk Level: {report['risk_level']}", 11, 20)

    line("Contributing Factors:", 12, 16, bold=True)
    for reason in report["contributing_factors"]:
        line(f"- {reason}", 10, 14)

    line("Recommended Action:", 12, 20, bold=True)
    line(report["recommended_action"], 10, 24)

    line("Timeline:", 12, 16, bold=True)
    for event in report["timeline"][:20]:
        line(f"{event['timestamp']} | {event['actor']} | {event['action']} | {event['status']}", 9, 12)
        if y < inch:
            c.showPage()
            y = height - inch

    c.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=incident_{incident_id}.pdf"},
    )
