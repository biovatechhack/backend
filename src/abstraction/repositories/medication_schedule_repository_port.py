from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.medication_schedule import MedicationSchedule


class MedicationScheduleRepositoryPort(ABC):
    @abstractmethod
    async def save(self, schedule: MedicationSchedule) -> str:
        """Persist a new schedule. Returns the saved schedule ID."""

    @abstractmethod
    async def get_by_id(self, schedule_id: str) -> MedicationSchedule | None:
        """Fetch a single schedule by primary key. Returns None if not found."""

    @abstractmethod
    async def get_all_active(self) -> list[MedicationSchedule]:
        """Return every active schedule across all patients (used for startup reload)."""

    @abstractmethod
    async def get_active_by_patient(self, patient_id: str) -> list[MedicationSchedule]:
        """Return all active schedules for a patient, ordered by scheduled_time."""

    @abstractmethod
    async def update(self, schedule: MedicationSchedule) -> None:
        """Overwrite scheduled_time, frequency, and active on an existing row."""

    @abstractmethod
    async def set_active(self, schedule_id: str, active: bool) -> None:
        """Enable or disable a schedule."""
