"""
Patient repository port — defines the interface the application layer
uses to persist and retrieve patients. Infrastructure details remain hidden.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class PatientRepository(ABC):

    @abstractmethod
    async def create(self, data: dict) -> dict:
        """Insert a new patient. Returns the created row as a dict."""

    @abstractmethod
    async def get_by_id(self, patient_id: str) -> Optional[dict]:
        """Return a single patient row or None if not found."""

    @abstractmethod
    async def list_all(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """Return a page of patient rows."""

    @abstractmethod
    async def update(self, patient_id: str, data: dict) -> Optional[dict]:
        """Patch a patient. Returns the updated row or None if not found."""

    @abstractmethod
    async def delete(self, patient_id: str) -> bool:
        """Delete a patient. Returns True if found and deleted."""
