from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class MedicationSchedule:
    patient_id: str
    medication: str
    scheduled_time: str   # "HH:MM" 24-hour
    frequency: str        # "daily" | "twice_daily"
    meal_context: str     # "before" | "after"
    active: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))
