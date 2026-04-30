from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRole(StrEnum):
    DOCTOR = "doctor"
    PATIENT = "patient"
    FAMILY = "family_member"

class UserBase(BaseModel):
    email: EmailStr
    role: UserRole

class Token(BaseModel):
    access_token: str
    token_type: str