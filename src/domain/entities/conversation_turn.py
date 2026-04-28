from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ConversationTurn:
    id: str
    conversation_log_id: str
    role: str
    content_darija: str
    turn_timestamp: datetime
    risk_at_turn: str | None = None
