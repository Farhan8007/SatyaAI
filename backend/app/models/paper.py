from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PaperBase(BaseModel):
    title: str
    subject: str
    exam_date: datetime
    exam_centre: Optional[str] = None


class PaperCreate(PaperBase):
    pass


class PaperOut(PaperBase):
    id: str
    setter_id: str
    setter_name: str
    status: ApprovalStatus
    sha256_hash: str
    signature: str
    is_encrypted: bool = True
    unlock_time: Optional[datetime] = None
    created_at: datetime
    remarks: Optional[str] = None


class PaperInDB(PaperOut):
    encrypted_blob: str  # base64 ciphertext stored server-side
