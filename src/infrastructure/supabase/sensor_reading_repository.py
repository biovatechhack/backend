from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from abstraction.repositories.sensor_reading_repository_port import SensorReadingRepositoryPort
from domain.entities.sensor_reading import SensorReading
from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)


def _row_to_reading(row: dict[str, Any]) -> SensorReading:
    ts = datetime.fromisoformat(row["recorded_at"])
    return SensorReading(
        patient_id=row["patient_id"],
        recorded_at=ts if ts.tzinfo else ts.replace(tzinfo=UTC),
        glucose_mg_dl=float(row["glucose_mg_dl"]),
        heart_rate_bpm=int(row["heart_rate_bpm"]),
        spo2_pct=int(row["spo2_pct"]),
        steps_today=int(row["steps_today"]),
        sleep_hours=float(row["sleep_hours"]),
    )


class SupabaseSensorReadingRepository(SensorReadingRepositoryPort):
    async def save(self, reading: SensorReading) -> None:
        client = await get_supabase_client()
        row = {
            "patient_id": reading.patient_id,
            "recorded_at": reading.recorded_at.isoformat(),
            "glucose_mg_dl": reading.glucose_mg_dl,
            "heart_rate_bpm": reading.heart_rate_bpm,
            "spo2_pct": reading.spo2_pct,
            "steps_today": reading.steps_today,
            "sleep_hours": reading.sleep_hours,
        }
        await client.table("sensor_readings").insert(row).execute()
        logger.info("sensor_reading saved patient=%s", reading.patient_id)

    async def get_by_patient_since(
        self, patient_id: str, since: datetime
    ) -> list[SensorReading]:
        client = await get_supabase_client()
        result = (
            await client.table("sensor_readings")
            .select("*")
            .eq("patient_id", patient_id)
            .gte("recorded_at", since.isoformat())
            .order("recorded_at", desc=True)
            .execute()
        )
        return [_row_to_reading(r) for r in result.data]
