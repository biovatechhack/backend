"""
Pydantic schemas for the Patient CRUD API.

Separate from the domain entity (Patient dataclass) — these are
wire-format models for request validation and response serialisation.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Request schemas ────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    """Body for POST /patients — all required fields to create a patient."""
    display_name: str = Field(..., min_length=2, max_length=120, examples=["Ahmed Benali"])
    age: int = Field(..., ge=0, le=120, examples=[58])
    gender: str = Field(..., pattern="^[MF]$", examples=["M"])
    bmi: float = Field(..., gt=0, lt=100, examples=[27.4])
    hba1c_last: float = Field(..., ge=0, lt=30, examples=[8.1])
    baseline_glucose: float = Field(..., gt=0, examples=[110.0])
    doctor_email: str = Field(..., examples=["dr.benali@clinic.dz"])
    medications: List[str] = Field(default_factory=list, examples=[["metformin 500mg"]])
    comorbidities: List[str] = Field(default_factory=list, examples=[["hypertension"]])


class PatientUpdate(BaseModel):
    """Body for PATCH /patients/{id} — all fields optional."""
    display_name: Optional[str] = Field(None, min_length=2, max_length=120)
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = Field(None, pattern="^[MF]$")
    bmi: Optional[float] = Field(None, gt=0, lt=100)
    hba1c_last: Optional[float] = Field(None, ge=0, lt=30)
    baseline_glucose: Optional[float] = Field(None, gt=0)
    doctor_email: Optional[str] = None
    medications: Optional[List[str]] = None
    comorbidities: Optional[List[str]] = None


# ── Response schema ────────────────────────────────────────────────────────────

class PatientResponse(BaseModel):
    """Full patient representation returned by all CRUD endpoints."""
    id: str
    display_name: str
    age: int
    gender: str
    bmi: float
    hba1c_last: float
    baseline_glucose: float
    doctor_email: str
    medications: List[str]
    comorbidities: List[str]
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True   # allows construction from ORM/dict


class PatientListResponse(BaseModel):
    """Paginated list wrapper."""
    total: int
    limit: int
    offset: int
    items: List[PatientResponse]
