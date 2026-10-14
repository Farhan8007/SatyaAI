from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class RiskLevel(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class Alert(BaseModel):
    id: str
    created_at: datetime
    user_id: str
    user_name: str
    risk_score: float          # 0-100
    risk_level: RiskLevel
    reasons: list[str]         # human-readable contributing factors
    confidence: float          # 0-1
    recommended_action: str
    related_paper_id: Optional[str] = None
    related_log_ids: list[str] = []
    resolved: bool = False
