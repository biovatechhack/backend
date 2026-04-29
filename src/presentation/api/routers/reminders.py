from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from application.services.reminder_service import ReminderService
from domain.entities.medication_schedule import MedicationSchedule
from domain.models.reminder_models import ReminderCreate, ReminderOut, ReminderPatch
from infrastructure.supabase.medication_schedule_repository import (
    SupabaseMedicationScheduleRepository,
)

reminders_router = APIRouter(prefix="/reminders", tags=["reminders"])


def _get_service() -> ReminderService:
    return ReminderService(repo=SupabaseMedicationScheduleRepository())


ServiceDep = Annotated[ReminderService, Depends(_get_service)]


def _to_out(s: MedicationSchedule) -> ReminderOut:
    return ReminderOut(
        id=s.id,
        patient_id=s.patient_id,
        medication=s.medication,
        scheduled_time=s.scheduled_time,
        frequency=s.frequency,
        meal_context=s.meal_context,
        active=s.active,
    )


@reminders_router.post(
    "",
    response_model=ReminderOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_reminder(body: ReminderCreate, svc: ServiceDep) -> ReminderOut:
    schedule = await svc.create(body)
    return _to_out(schedule)


@reminders_router.get(
    "/{patient_id}",
    response_model=list[ReminderOut],
)
async def list_reminders(patient_id: str, svc: ServiceDep) -> list[ReminderOut]:
    schedules = await svc.list_active(patient_id)
    return [_to_out(s) for s in schedules]


@reminders_router.patch(
    "/{schedule_id}",
    response_model=ReminderOut,
)
async def update_reminder(
    schedule_id: str, body: ReminderPatch, svc: ServiceDep
) -> ReminderOut:
    schedule = await svc.update(schedule_id, body)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return _to_out(schedule)


@reminders_router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_reminder(schedule_id: str, svc: ServiceDep) -> None:
    found = await svc.deactivate(schedule_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
