from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class AdherenceIn(BaseModel):
    patient_id: str
    medication: str
    taken: bool
    meal_context: Literal["before", "after", "with"]

    @field_validator("patient_id", "medication")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class AdherenceOut(BaseModel):
    id: str
    patient_id: str
    medication: str
    scheduled_at: datetime
    taken: bool
    meal_context: str
    confirmed_at: datetime | None


class AdherenceSummary(BaseModel):
    total_scheduled: int
    total_taken: int
    adherence_pct: float


class AdherenceHistoryOut(BaseModel):
    summary: AdherenceSummary
    logs: list[AdherenceOut]
