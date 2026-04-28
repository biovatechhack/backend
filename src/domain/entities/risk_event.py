from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class RiskEvent:
    id: str
    patient_id: str
    conversation_log_id: str
    risk_level: str
    confidence: float
    timestamp: datetime
    extracted_symptoms: list[str] = field(default_factory=list)
    glucose_reading: float | None = None
    top_decision_features: list[str] = field(default_factory=list)
    biometric_passed: bool = False
    alerts_sent: list[str] = field(default_factory=list)
