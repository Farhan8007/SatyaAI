from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Role(str, Enum):
    admin = "administrator"
    paper_setter = "paper_setter"
    moderator = "moderator"
    exam_centre = "examination_centre"
    auditor = "security_auditor"


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: Role
    institution: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(UserBase):
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    email_verified: bool = False


class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    failed_login_count: int = 0
    known_devices: list[str] = Field(default_factory=list)
    known_ips: list[str] = Field(default_factory=list)
    email_verified: bool = False
    verification_token: Optional[str] = None
