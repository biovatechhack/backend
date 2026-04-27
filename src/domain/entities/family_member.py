from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class FamilyMember:
    id: str
    patient_id: str
    name: str
    relationship: str
    phone_whatsapp: str
    created_at: datetime
    alert_preferences: list[str] = field(default_factory=list)
    dashboard_access: str = "full"
