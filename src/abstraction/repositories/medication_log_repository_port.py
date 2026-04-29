from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.medication_log import MedicationLog


class MedicationLogRepositoryPort(ABC):
    @abstractmethod
    async def save(self, log: MedicationLog) -> str:
        """Persist a medication log entry. Returns the saved log ID."""

    @abstractmethod
    async def get_by_patient_since(
        self, patient_id: str, since: datetime
    ) -> list[MedicationLog]:
        """Return all log entries for a patient on or after `since`, newest first."""
