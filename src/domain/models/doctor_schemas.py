"""
Pydantic schemas for the Doctor CRUD API.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    specialty: str = Field(..., max_length=120)
    clinic: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=32)
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    experience_years: int = Field(0, ge=0)


class DoctorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    specialty: Optional[str] = Field(None, max_length=120)
    clinic: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=32)
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    experience_years: Optional[int] = Field(None, ge=0)


class DoctorResponse(BaseModel):
    id: str
    name: str
    email: str
    specialty: str
    clinic: Optional[str]
    phone: Optional[str]
    bio: Optional[str]
    profile_picture_url: Optional[str]
    experience_years: int
    created_at: datetime

    class Config:
        from_attributes = True


class DoctorListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[DoctorResponse]
