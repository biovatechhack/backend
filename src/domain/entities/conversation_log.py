from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from domain.entities.conversation_turn import ConversationTurn
from domain.entities.risk_event import RiskEvent


@dataclass(slots=True)
class ConversationLog:
    id: str
    patient_id: str
    final_risk: str
    duration_seconds: int
    gemini_calls: int
    pii_stripped: bool
    created_at: datetime
    turns: list[ConversationTurn] = field(default_factory=list)
    risk_events: list[RiskEvent] = field(default_factory=list)
