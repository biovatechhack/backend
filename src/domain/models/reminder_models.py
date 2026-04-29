from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ReminderCreate(BaseModel):
    patient_id: str
    medication: str
    scheduled_time: str          # "HH:MM" 24-hour
    frequency: Literal["daily", "twice_daily"]
    meal_context: Literal["before", "after"]

    @field_validator("scheduled_time")
    @classmethod
    def _validate_time(cls, v: str) -> str:
        if not _TIME_RE.match(v):
            raise ValueError("scheduled_time must be HH:MM (24-hour)")
        return v


class ReminderPatch(BaseModel):
    scheduled_time: str | None = None
    frequency: Literal["daily", "twice_daily"] | None = None

    @field_validator("scheduled_time")
    @classmethod
    def _validate_time(cls, v: str | None) -> str | None:
        if v is not None and not _TIME_RE.match(v):
            raise ValueError("scheduled_time must be HH:MM (24-hour)")
        return v


class ReminderOut(BaseModel):
    id: str
    patient_id: str
    medication: str
    scheduled_time: str
    frequency: str
    meal_context: str
    active: bool
