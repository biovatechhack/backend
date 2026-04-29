"""
Patient CRUD router
===================
REST endpoints for creating, reading, updating, and deleting patients.

Base path: /api/v1/patients
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from application.use_cases.patient_usecase import PatientUseCase
from domain.models.patient_schemas import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from infrastructure.supabase.patient_repository import SupabasePatientRepository


# ── Dependency ────────────────────────────────────────────────────────────────

def get_patient_use_case() -> PatientUseCase:
    """Wire the concrete Supabase repo into the use case."""
    return PatientUseCase(repo=SupabasePatientRepository())


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/patients", tags=["patients"])


# ── POST /patients ─────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient",
)
async def create_patient(
    payload: PatientCreate,
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> PatientResponse:
    """
    Register a new diabetic patient.

    Returns the created patient record including the generated **id** and **created_at**.
    """
    return await use_case.create_patient(payload)


# ── GET /patients ──────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=PatientListResponse,
    summary="List all patients (paginated)",
)
async def list_patients(
    limit: int = Query(default=50, ge=1, le=200, description="Max rows to return"),
    offset: int = Query(default=0, ge=0, description="Rows to skip"),
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> PatientListResponse:
    """Return a paginated list of all patients, ordered by creation date (newest first)."""
    return await use_case.list_patients(limit=limit, offset=offset)


# ── GET /patients/{patient_id} ─────────────────────────────────────────────────

@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get a single patient by ID",
)
async def get_patient(
    patient_id: str,
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> PatientResponse:
    """Retrieve a patient by their UUID. Returns **404** if not found."""
    patient = await use_case.get_patient(patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    return patient


# ── PATCH /patients/{patient_id} ───────────────────────────────────────────────

@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Partially update a patient",
)
async def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> PatientResponse:
    """
    Update one or more fields of a patient record.
    Only the fields you provide will be changed; omitted fields are untouched.
    Returns **404** if the patient does not exist.
    """
    updated = await use_case.update_patient(patient_id, payload)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    return updated


# ── DELETE /patients/{patient_id} ──────────────────────────────────────────────

@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a patient",
)
async def delete_patient(
    patient_id: str,
    use_case: PatientUseCase = Depends(get_patient_use_case),
) -> None:
    """
    Permanently delete a patient and all their related records (cascade).
    Returns **404** if the patient does not exist, **204 No Content** on success.
    """
    deleted = await use_case.delete_patient(patient_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
