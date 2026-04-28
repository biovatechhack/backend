"""
Patient CRUD use case
=====================
Thin orchestration layer between the API router and the repository.
Handles validation logic that is too domain-specific for the router,
and converts repository dicts to PatientResponse schemas.
"""
from __future__ import annotations

from typing import List, Optional

from abstraction.repositories.patient_repository import PatientRepository
from domain.models.patient_schemas import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)


class PatientUseCase:
    """CRUD orchestrator for the Patient aggregate."""

    def __init__(self, repo: PatientRepository) -> None:
        self.repo = repo

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_patient(self, payload: PatientCreate) -> PatientResponse:
        """
        Persist a new patient and return the full record.
        Raises RuntimeError if the database operation fails.
        """
        row = await self.repo.create(payload.model_dump())
        return PatientResponse(**row)

    # ── Read (single) ─────────────────────────────────────────────────────────

    async def get_patient(self, patient_id: str) -> Optional[PatientResponse]:
        """
        Return one patient by id, or None if not found.
        The router decides whether to raise 404.
        """
        row = await self.repo.get_by_id(patient_id)
        return PatientResponse(**row) if row else None

    # ── Read (list) ───────────────────────────────────────────────────────────

    async def list_patients(
        self, limit: int = 50, offset: int = 0
    ) -> PatientListResponse:
        """Return a paginated list of patients."""
        rows = await self.repo.list_all(limit=limit, offset=offset)
        items = [PatientResponse(**r) for r in rows]
        return PatientListResponse(
            total=len(items),   # Supabase count(*) requires an extra call; use len for now
            limit=limit,
            offset=offset,
            items=items,
        )

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_patient(
        self, patient_id: str, payload: PatientUpdate
    ) -> Optional[PatientResponse]:
        """
        Apply a partial update.
        Returns the updated record, or None if not found.
        """
        row = await self.repo.update(
            patient_id,
            payload.model_dump(exclude_none=True),
        )
        return PatientResponse(**row) if row else None

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_patient(self, patient_id: str) -> bool:
        """
        Remove a patient.
        Returns True if deleted, False if not found.
        """
        return await self.repo.delete(patient_id)
