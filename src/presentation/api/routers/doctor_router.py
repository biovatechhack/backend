"""
Doctor CRUD router.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from application.use_cases.doctor_usecase import DoctorUseCase
from domain.models.doctor_schemas import (
    DoctorCreate,
    DoctorListResponse,
    DoctorResponse,
    DoctorUpdate,
)
from infrastructure.supabase.doctor_repository import SupabaseDoctorRepository


def get_doctor_use_case() -> DoctorUseCase:
    return DoctorUseCase(repo=SupabaseDoctorRepository())


router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    payload: DoctorCreate,
    use_case: DoctorUseCase = Depends(get_doctor_use_case),
) -> DoctorResponse:
    return await use_case.create_doctor(payload)


@router.get("/", response_model=DoctorListResponse)
async def list_doctors(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    use_case: DoctorUseCase = Depends(get_doctor_use_case),
) -> DoctorListResponse:
    return await use_case.list_doctors(limit=limit, offset=offset)


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: str,
    use_case: DoctorUseCase = Depends(get_doctor_use_case),
) -> DoctorResponse:
    doctor = await use_case.get_doctor(doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.patch("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: str,
    payload: DoctorUpdate,
    use_case: DoctorUseCase = Depends(get_doctor_use_case),
) -> DoctorResponse:
    updated = await use_case.update_doctor(doctor_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return updated


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(
    doctor_id: str,
    use_case: DoctorUseCase = Depends(get_doctor_use_case),
) -> None:
    deleted = await use_case.delete_doctor(doctor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Doctor not found")
