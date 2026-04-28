from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from domain.entities.conversation_log import ConversationLog
from domain.entities.family_member import FamilyMember
from domain.entities.medication_log import MedicationLog
from domain.entities.risk_event import RiskEvent


@dataclass(slots=True)
class Patient:
    id: str
    display_name: str
    age: int
    bmi: float
    hba1c_last: float
    baseline_glucose: float
    doctor_email: str
    created_at: datetime
    medications: list[str] = field(default_factory=list)
    comorbidities: list[str] = field(default_factory=list)
    family_members: list[FamilyMember] = field(default_factory=list)
    medication_logs: list[MedicationLog] = field(default_factory=list)
    conversation_logs: list[ConversationLog] = field(default_factory=list)
    risk_events: list[RiskEvent] = field(default_factory=list)
