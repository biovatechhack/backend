"""
Doctor CRUD use case.
"""
from __future__ import annotations

from typing import List, Optional

from abstraction.repositories.doctor_repository import DoctorRepository
from domain.models.doctor_schemas import (
    DoctorCreate,
    DoctorListResponse,
    DoctorResponse,
    DoctorUpdate,
)


class DoctorUseCase:
    def __init__(self, repo: DoctorRepository) -> None:
        self.repo = repo

    async def create_doctor(self, payload: DoctorCreate) -> DoctorResponse:
        row = await self.repo.create(payload.model_dump())
        return DoctorResponse(**row)

    async def get_doctor(self, doctor_id: str) -> Optional[DoctorResponse]:
        row = await self.repo.get_by_id(doctor_id)
        return DoctorResponse(**row) if row else None

    async def list_doctors(self, limit: int = 50, offset: int = 0) -> DoctorListResponse:
        rows = await self.repo.list_all(limit=limit, offset=offset)
        items = [DoctorResponse(**r) for r in rows]
        return DoctorListResponse(
            total=len(items),
            limit=limit,
            offset=offset,
            items=items,
        )

    async def update_doctor(self, doctor_id: str, payload: DoctorUpdate) -> Optional[DoctorResponse]:
        row = await self.repo.update(doctor_id, payload.model_dump(exclude_none=True))
        return DoctorResponse(**row) if row else None

    async def delete_doctor(self, doctor_id: str) -> bool:
        return await self.repo.delete(doctor_id)
