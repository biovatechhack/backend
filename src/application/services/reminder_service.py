from __future__ import annotations

import logging

from abstraction.repositories.medication_schedule_repository_port import (
    MedicationScheduleRepositoryPort,
)
from domain.entities.medication_schedule import MedicationSchedule
from domain.models.reminder_models import ReminderCreate, ReminderPatch
from infrastructure.scheduler import register_reminder, unregister_reminder

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, repo: MedicationScheduleRepositoryPort) -> None:
        self._repo = repo

    async def create(self, data: ReminderCreate) -> MedicationSchedule:
        schedule = MedicationSchedule(
            patient_id=data.patient_id,
            medication=data.medication,
            scheduled_time=data.scheduled_time,
            frequency=data.frequency,
            meal_context=data.meal_context,
        )
        await self._repo.save(schedule)
        register_reminder(schedule)
        logger.info("reminder.create id=%s patient=%s", schedule.id, schedule.patient_id)
        return schedule

    async def list_active(self, patient_id: str) -> list[MedicationSchedule]:
        return await self._repo.get_active_by_patient(patient_id)

    async def update(self, schedule_id: str, patch: ReminderPatch) -> MedicationSchedule | None:
        schedule = await self._repo.get_by_id(schedule_id)
        if schedule is None:
            return None
        if patch.scheduled_time is not None:
            schedule.scheduled_time = patch.scheduled_time
        if patch.frequency is not None:
            schedule.frequency = patch.frequency
        await self._repo.update(schedule)
        unregister_reminder(schedule_id)
        register_reminder(schedule)
        logger.info("reminder.update id=%s", schedule_id)
        return schedule

    async def deactivate(self, schedule_id: str) -> bool:
        schedule = await self._repo.get_by_id(schedule_id)
        if schedule is None:
            return False
        await self._repo.set_active(schedule_id, active=False)
        unregister_reminder(schedule_id)
        logger.info("reminder.deactivate id=%s", schedule_id)
        return True
