from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, date, time, timedelta
from uuid import uuid4

from abstraction.repositories.medication_log_repository_port import MedicationLogRepositoryPort
from abstraction.repositories.medication_schedule_repository_port import MedicationScheduleRepositoryPort
from domain.entities.medication_log import MedicationLog
from domain.exceptions import PatientNotFoundError


@dataclass(slots=True)
class AdherenceHistory:
    logs: list[MedicationLog]
    total_scheduled: int
    total_taken: int
    adherence_pct: float


class AdherenceService:
    def __init__(
        self,
        schedule_repo: MedicationScheduleRepositoryPort,
        log_repo: MedicationLogRepositoryPort,
    ) -> None:
        self._schedule_repo = schedule_repo
        self._log_repo = log_repo

    async def confirm_dose(
        self,
        patient_id: str,
        medication: str,
        taken: bool,
        meal_context: str,
    ) -> MedicationLog:
        schedules = await self._schedule_repo.get_active_by_patient(patient_id)
        if not schedules:
            raise PatientNotFoundError(patient_id)

        schedule = next(
            (s for s in schedules if s.medication.lower() == medication.lower()),
            schedules[0],
        )

        hour, minute = (int(p) for p in schedule.scheduled_time.split(":"))
        scheduled_at = datetime.combine(date.today(), time(hour, minute), tzinfo=UTC)

        log = MedicationLog(
            id=str(uuid4()),
            patient_id=patient_id,
            medication=medication,
            scheduled_at=scheduled_at,
            taken=taken,
            meal_context=meal_context,
            confirmed_at=datetime.now(UTC),
        )
        await self._log_repo.save(log)
        return log

    async def get_history(self, patient_id: str, days: int) -> AdherenceHistory:
        since = datetime.now(UTC) - timedelta(days=days)
        logs = await self._log_repo.get_by_patient_since(patient_id, since)
        total_scheduled = len(logs)
        total_taken = sum(1 for lg in logs if lg.taken)
        adherence_pct = (total_taken / total_scheduled * 100) if total_scheduled else 0.0
        return AdherenceHistory(
            logs=logs,
            total_scheduled=total_scheduled,
            total_taken=total_taken,
            adherence_pct=round(adherence_pct, 1),
        )
