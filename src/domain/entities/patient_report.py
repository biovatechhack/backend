from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from domain.entities.medication_schedule import MedicationSchedule
from domain.entities.patient import Patient
from domain.entities.risk_event import RiskEvent
from domain.entities.sensor_reading import SensorReading


@dataclass(slots=True)
class PatientReport:
    patient: Patient
    risk_events: list[RiskEvent]
    sensor_readings: list[SensorReading]
    medication_schedules: list[MedicationSchedule]
    days: int
    generated_at: datetime
    risk_events_count: dict[str, int] = field(default_factory=dict)
