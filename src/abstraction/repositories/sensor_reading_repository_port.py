from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.sensor_reading import SensorReading


class SensorReadingRepositoryPort(ABC):
    @abstractmethod
    async def get_by_patient_since(
        self, patient_id: str, since: datetime
    ) -> list[SensorReading]:
        """Return all sensor readings for a patient on or after *since*, newest first."""
