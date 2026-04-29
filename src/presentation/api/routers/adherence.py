from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from application.services.adherence_service import AdherenceService
from domain.exceptions import PatientNotFoundError
from infrastructure.supabase.medication_log_repository import SupabaseMedicationLogRepository
from infrastructure.supabase.medication_schedule_repository import SupabaseMedicationScheduleRepository
from presentation.api.dtos.adherence_dtos import AdherenceHistoryOut, AdherenceIn, AdherenceOut, AdherenceSummary

adherence_router = APIRouter(prefix="/adherence", tags=["adherence"])


def _get_service() -> AdherenceService:
    return AdherenceService(
        schedule_repo=SupabaseMedicationScheduleRepository(),
        log_repo=SupabaseMedicationLogRepository(),
    )


ServiceDep = Annotated[AdherenceService, Depends(_get_service)]


@adherence_router.post("", status_code=status.HTTP_201_CREATED, response_model=AdherenceOut)
async def confirm_adherence(body: AdherenceIn, svc: ServiceDep) -> AdherenceOut:
    try:
        log = await svc.confirm_dose(
            patient_id=body.patient_id,
            medication=body.medication,
            taken=body.taken,
            meal_context=body.meal_context,
        )
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active schedules found for patient {body.patient_id!r}",
        ) from exc
    return AdherenceOut(
        id=log.id,
        patient_id=log.patient_id,
        medication=log.medication,
        scheduled_at=log.scheduled_at,
        taken=log.taken,
        meal_context=log.meal_context,
        confirmed_at=log.confirmed_at,
    )


@adherence_router.get("/{patient_id}", response_model=AdherenceHistoryOut)
async def get_adherence_history(
    patient_id: str,
    svc: ServiceDep,
    days: int = Query(7, ge=1, le=90, description="Number of past days to include"),
) -> AdherenceHistoryOut:
    history = await svc.get_history(patient_id, days)
    return AdherenceHistoryOut(
        summary=AdherenceSummary(
            total_scheduled=history.total_scheduled,
            total_taken=history.total_taken,
            adherence_pct=history.adherence_pct,
        ),
        logs=[
            AdherenceOut(
                id=lg.id,
                patient_id=lg.patient_id,
                medication=lg.medication,
                scheduled_at=lg.scheduled_at,
                taken=lg.taken,
                meal_context=lg.meal_context,
                confirmed_at=lg.confirmed_at,
            )
            for lg in history.logs
        ],
    )
