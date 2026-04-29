"""
Doctor repository port.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class DoctorRepositoryPort(ABC):

    @abstractmethod
    async def create(self, data: dict) -> dict:
        """Insert a new doctor."""

    @abstractmethod
    async def get_by_id(self, doctor_id: str) -> Optional[dict]:
        """Return a single doctor row."""

    @abstractmethod
    async def list_all(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """Return a page of doctors."""

    @abstractmethod
    async def update(self, doctor_id: str, data: dict) -> Optional[dict]:
        """Update a doctor."""

    @abstractmethod
    async def delete(self, doctor_id: str) -> bool:
        """Delete a doctor."""
