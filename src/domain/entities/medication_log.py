from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class MedicationLog:
    id: str
    patient_id: str
    medication: str
    scheduled_at: datetime
    taken: bool
    meal_context: str
    confirmed_at: datetime | None = None
