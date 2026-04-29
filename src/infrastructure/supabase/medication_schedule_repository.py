from __future__ import annotations

import logging
from typing import Any

from abstraction.repositories.medication_schedule_repository_port import (
    MedicationScheduleRepositoryPort,
)
from domain.entities.medication_schedule import MedicationSchedule
from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)

_TABLE = "medication_schedules"


def _row_to_schedule(row: dict[str, Any]) -> MedicationSchedule:
    return MedicationSchedule(
        id=row["id"],
        patient_id=row["patient_id"],
        medication=row["medication"],
        scheduled_time=row["scheduled_time"],
        frequency=row["frequency"],
        meal_context=row["meal_context"],
        active=bool(row["active"]),
    )


def _schedule_to_row(schedule: MedicationSchedule) -> dict[str, Any]:
    return {
        "id": schedule.id,
        "patient_id": schedule.patient_id,
        "medication": schedule.medication,
        "scheduled_time": schedule.scheduled_time,
        "frequency": schedule.frequency,
        "meal_context": schedule.meal_context,
        "active": schedule.active,
    }


class SupabaseMedicationScheduleRepository(MedicationScheduleRepositoryPort):
    async def save(self, schedule: MedicationSchedule) -> str:
        client = await get_supabase_client()
        await client.table(_TABLE).insert(_schedule_to_row(schedule)).execute()
        logger.info("medication_schedule saved id=%s patient=%s", schedule.id, schedule.patient_id)
        return schedule.id

    async def get_by_id(self, schedule_id: str) -> MedicationSchedule | None:
        client = await get_supabase_client()
        result = (
            await client.table(_TABLE).select("*").eq("id", schedule_id).limit(1).execute()
        )
        return _row_to_schedule(result.data[0]) if result.data else None

    async def get_all_active(self) -> list[MedicationSchedule]:
        client = await get_supabase_client()
        result = (
            await client.table(_TABLE)
            .select("*")
            .eq("active", True)
            .order("scheduled_time")
            .execute()
        )
        return [_row_to_schedule(r) for r in result.data]

    async def get_active_by_patient(self, patient_id: str) -> list[MedicationSchedule]:
        client = await get_supabase_client()
        result = (
            await client.table(_TABLE)
            .select("*")
            .eq("patient_id", patient_id)
            .eq("active", True)
            .order("scheduled_time")
            .execute()
        )
        return [_row_to_schedule(r) for r in result.data]

    async def update(self, schedule: MedicationSchedule) -> None:
        client = await get_supabase_client()
        await (
            client.table(_TABLE)
            .update({
                "scheduled_time": schedule.scheduled_time,
                "frequency": schedule.frequency,
                "active": schedule.active,
            })
            .eq("id", schedule.id)
            .execute()
        )
        logger.info("medication_schedule updated id=%s", schedule.id)

    async def set_active(self, schedule_id: str, active: bool) -> None:
        client = await get_supabase_client()
        await (
            client.table(_TABLE)
            .update({"active": active})
            .eq("id", schedule_id)
            .execute()
        )
        logger.info("medication_schedule id=%s active=%s", schedule_id, active)
