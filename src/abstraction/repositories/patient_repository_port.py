from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.patient import Patient


class PatientRepositoryPort(ABC):
    @abstractmethod
    async def get_by_id(self, patient_id: str) -> Patient | None:
        """Fetch a patient by ID without relations. Returns None if not found."""

    @abstractmethod
    async def get_with_family(self, patient_id: str) -> Patient | None:
        """Fetch a patient with family_members populated. Returns None if not found."""
