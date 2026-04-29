from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.risk_event import RiskEvent


class RiskEventRepositoryPort(ABC):
    @abstractmethod
    async def save(self, event: RiskEvent) -> str:
        """Persist a new risk event. Returns the saved event ID."""

    @abstractmethod
    async def update_alerts_sent(self, event_id: str, channels: list[str]) -> None:
        """Overwrite alerts_sent with the provided channel list."""

    @abstractmethod
    async def get_by_patient_since(
        self, patient_id: str, since: datetime
    ) -> list[RiskEvent]:
        """Return all risk events for a patient on or after *since*, newest first."""
