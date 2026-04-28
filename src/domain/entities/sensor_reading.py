from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class SensorReading:
    patient_id: str
    recorded_at: datetime
    glucose_mg_dl: float
    heart_rate_bpm: int
    spo2_pct: int
    steps_today: int
    sleep_hours: float
