"""
Central place where every audit-log entry is written. Every entry is
hash-chained to the previous one (tamper-evidence) and its behavioural
features are computed inline so the AI engine can score it immediately.

Day 2 change (Security Lead): hash-chain writes are now serialized with an
asyncio.Lock so concurrent requests can't fork the chain by reading the same
prev_hash before either inserts.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional

from app.database import database
from app.security.encryption import sha256_hash, chain_hash
from app.ai.anomaly_detector import AnomalyDetector, risk_level_from_score
from app.ai.explainer import explain

# A single in-process detector instance, retrained periodically from seed data
# or a scheduled job in a production deployment. Kept simple here for clarity.
_detector: Optional[AnomalyDetector] = None

# Day 2: Serialize hash-chain read→compute→insert so concurrent requests
# can't read the same prev_hash before either has inserted, which would fork
# the chain and break verify-integrity. Loop-safe to support multiple event loops.
_chain_lock: Optional[asyncio.Lock] = None
_chain_lock_loop: Optional[asyncio.AbstractEventLoop] = None


def get_chain_lock() -> asyncio.Lock:
    """Return an asyncio.Lock bound to the current running event loop."""
    global _chain_lock, _chain_lock_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _chain_lock is None or _chain_lock_loop != current_loop:
        _chain_lock = asyncio.Lock()
        _chain_lock_loop = current_loop
    return _chain_lock


def set_detector(detector: AnomalyDetector) -> None:
    global _detector
    _detector = detector


async def _get_last_hash() -> str:
    last = await database.audit_logs.find_one(sort=[("timestamp", -1)])
    return last["hash"] if last else "GENESIS"


async def record_audit_log(
    user_id: str,
    user_name: str,
    role: str,
    ip_address: str,
    device: str,
    action: str,
    status: str,
    paper_id: Optional[str] = None,
    browser: str = "unknown",
    location: str = "unknown",
    is_new_device: bool = False,
    is_new_ip: bool = False,
    downloads_last_hour: int = 0,
    locations_last_24h: int = 1,
    is_bulk_download: bool = False,
    skipped_approval: bool = False,
    permission_escalation: bool = False,
) -> dict:
    # MongoDB stores datetimes at millisecond precision, so we truncate here
    # too -- otherwise the hash computed pre-insert (with microseconds) would
    # never match a hash recomputed from a value read back from the DB.
    now = datetime.utcnow()
    timestamp = now.replace(microsecond=(now.microsecond // 1000) * 1000)

    entry_id = str(uuid.uuid4())
    features = {
        "hour_of_day": timestamp.hour,
        "is_new_device": is_new_device,
        "is_new_ip": is_new_ip,
        "is_failed_login": status == "FAILED",
        "downloads_last_hour": downloads_last_hour,
        "locations_last_24h": locations_last_24h,
        "is_bulk_download": is_bulk_download,
        "skipped_approval": skipped_approval,
        "permission_escalation": permission_escalation,
    }

    # Day 2: Critical section — read prev_hash, compute chain hash, insert.
    # Serialized so concurrent requests can't read the same prev_hash.
    async with get_chain_lock():
        prev_hash = await _get_last_hash()

        entry_data = f"{entry_id}|{user_id}|{action}|{status}|{timestamp.isoformat()}"
        entry_hash = chain_hash(prev_hash, entry_data)

        doc = {
            "id": entry_id,
            "timestamp": timestamp,
            "user_id": user_id,
            "user_name": user_name,
            "role": role,
            "ip_address": ip_address,
            "location": location,
            "device": device,
            "browser": browser,
            "action": action,
            "paper_id": paper_id,
            "status": status,
            "hash": entry_hash,
            "prev_hash": prev_hash,
            **features,
        }
        await database.audit_logs.insert_one(doc)

    # Run this entry through the AI engine immediately if a detector is loaded.
    if _detector is not None and _detector._is_fitted:
        result = _detector.score(features)
        if result.is_anomaly or result.risk_score >= 35:
            explanation = explain(features, result.risk_score)
            alert_doc = {
                "id": str(uuid.uuid4()),
                "created_at": timestamp,
                "user_id": user_id,
                "user_name": user_name,
                "risk_score": result.risk_score,
                "risk_level": risk_level_from_score(result.risk_score),
                "reasons": explanation.reasons,
                "confidence": explanation.confidence,
                "recommended_action": explanation.recommended_action,
                "related_paper_id": paper_id,
                "related_log_ids": [entry_id],
                "resolved": False,
            }
            await database.alerts.insert_one(alert_doc)

    return doc


def verify_chain_integrity(logs: list[dict]) -> bool:
    """Recompute the hash chain over a sequence of logs to detect tampering."""
    prev_hash = "GENESIS"
    for log in sorted(logs, key=lambda l: l["timestamp"]):
        entry_data = f"{log['id']}|{log['user_id']}|{log['action']}|{log['status']}|{log['timestamp'].isoformat()}"
        expected = chain_hash(prev_hash, entry_data)
        if expected != log["hash"]:
            return False
        prev_hash = log["hash"]
    return True


def verify_chain(logs: Optional[list[dict]] = None):
    """Verify hash chain integrity.

    If logs is provided, synchronously verifies the given list of log dicts.
    If logs is None, returns a coroutine that queries database.audit_logs
    and verifies the whole persisted chain.
    """
    if logs is not None:
        return verify_chain_integrity(logs)

    async def _verify_db_chain() -> bool:
        cursor = database.audit_logs.find().sort("timestamp", 1)
        db_logs = [doc async for doc in cursor]
        return verify_chain_integrity(db_logs)

    return _verify_db_chain()
