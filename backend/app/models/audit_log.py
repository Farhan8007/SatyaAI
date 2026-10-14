from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime
    user_id: str
    user_name: str
    role: str
    ip_address: str
    location: str
    device: str
    browser: str
    action: str          # e.g. LOGIN, DOWNLOAD, UPLOAD, APPROVE, REJECT, UNLOCK
    paper_id: Optional[str] = None
    status: str           # SUCCESS, FAILED
    hash: str             # hash of this log entry, chained for tamper-evidence
    prev_hash: Optional[str] = None

    # Features used by the anomaly detector (derived at write time)
    hour_of_day: int
    is_new_device: bool
    is_new_ip: bool
    is_failed_login: bool
