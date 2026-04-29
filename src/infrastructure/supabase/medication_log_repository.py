from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from abstraction.repositories.medication_log_repository_port import MedicationLogRepositoryPort
from domain.entities.medication_log import MedicationLog
from infrastructure.config.settings import settings
from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)

_TABLE = "medication_logs"


def _row_to_log(row: dict[str, Any]) -> MedicationLog:
    def _parse(v: str | None) -> datetime | None:
        if v is None:
            return None
        dt = datetime.fromisoformat(v)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

    scheduled = datetime.fromisoformat(row["scheduled_at"])
    return MedicationLog(
        id=row["id"],
        patient_id=row["patient_id"],
        medication=row["medication"],
        scheduled_at=scheduled if scheduled.tzinfo else scheduled.replace(tzinfo=UTC),
        taken=bool(row["taken"]),
        meal_context=row["meal_context"],
        confirmed_at=_parse(row.get("confirmed_at")),
    )


def _log_to_row(log: MedicationLog) -> dict:
    return {
        "id": log.id,
        "patient_id": log.patient_id,
        "medication": log.medication,
        "scheduled_at": log.scheduled_at.isoformat(),
        "taken": log.taken,
        "meal_context": log.meal_context,
        "confirmed_at": log.confirmed_at.isoformat() if log.confirmed_at else None,
    }


async def _broadcast_realtime(patient_id: str, payload: dict) -> None:
    url = f"{settings.SUPABASE_URL}/realtime/v1/api/broadcast"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY or "",
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY or ''}",
        "Content-Type": "application/json",
    }
    body = {
        "messages": [
            {
                "topic": f"patient:{patient_id}",
                "event": "adherence_update",
                "payload": payload,
            }
        ]
    }
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code >= 400:
            logger.warning("realtime broadcast failed status=%s", resp.status_code)


class SupabaseMedicationLogRepository(MedicationLogRepositoryPort):
    async def save(self, log: MedicationLog) -> str:
        client = await get_supabase_client()
        await client.table(_TABLE).insert(_log_to_row(log)).execute()
        logger.info("medication_log saved id=%s patient=%s taken=%s", log.id, log.patient_id, log.taken)

        try:
            await _broadcast_realtime(
                log.patient_id,
                {
                    "medication": log.medication,
                    "taken": log.taken,
                    "confirmed_at": log.confirmed_at.isoformat() if log.confirmed_at else None,
                },
            )
        except Exception as exc:
            logger.warning("realtime broadcast error: %s", exc)

        return log.id

    async def get_by_patient_since(
        self, patient_id: str, since: datetime
    ) -> list[MedicationLog]:
        client = await get_supabase_client()
        result = (
            await client.table(_TABLE)
            .select("*")
            .eq("patient_id", patient_id)
            .gte("scheduled_at", since.isoformat())
            .order("scheduled_at", desc=True)
            .execute()
        )
        return [_row_to_log(r) for r in result.data]
