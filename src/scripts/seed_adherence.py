"""
Seed 30 days of MedicationLog rows for the demo patient.
Schedule: Metformin 500mg twice daily — 08:00 (after breakfast) and 20:00 (after dinner).
Adherence rate: ~85% (roughly 5 missed doses out of 60).

Run from src/:
    PYTHONPATH=. ../hackathon-env/bin/python scripts/seed_adherence.py
"""
from __future__ import annotations

import asyncio
import random
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

from infrastructure.supabase.client import get_supabase_client

_PREFERRED_EMAIL = "dr.hassan@clinique.dz"
_MEDICATION = "Metformin 500mg"
_DOSES: list[tuple[time, str]] = [
    (time(8, 0), "after"),
    (time(20, 0), "after"),
]
_DAYS = 30
_ADHERENCE_RATE = 0.85
_LOG_TABLE = "medication_logs"
_SCHEDULE_TABLE = "medication_schedules"


async def _resolve_patient_id(client) -> str:
    # Try preferred demo patient first
    result = (
        await client.table("patients")
        .select("id,display_name")
        .eq("doctor_email", _PREFERRED_EMAIL)
        .limit(1)
        .execute()
    )
    if result.data:
        row = result.data[0]
        print(f"Using preferred demo patient: {row['display_name']} ({row['id']})")
        return row["id"]

    # Fall back to first available patient
    result = (
        await client.table("patients")
        .select("id,display_name")
        .limit(1)
        .execute()
    )
    if not result.data:
        raise SystemExit("No patients found in Supabase. Seed a patient first.")
    row = result.data[0]
    print(f"Using existing patient: {row['display_name']} ({row['id']})")
    return row["id"]


async def _ensure_schedule(client, patient_id: str) -> None:
    result = (
        await client.table(_SCHEDULE_TABLE)
        .select("id")
        .eq("patient_id", patient_id)
        .eq("medication", _MEDICATION)
        .limit(1)
        .execute()
    )
    if result.data:
        print(f"Medication schedule already exists for {_MEDICATION}")
        return

    rows = [
        {
            "id": str(uuid4()),
            "patient_id": patient_id,
            "medication": _MEDICATION,
            "scheduled_time": "08:00",
            "frequency": "twice_daily",
            "meal_context": "after",
            "active": True,
        },
    ]
    await client.table(_SCHEDULE_TABLE).insert(rows).execute()
    print(f"Created medication schedule for {_MEDICATION}")


async def _already_seeded(client, patient_id: str) -> bool:
    result = (
        await client.table(_LOG_TABLE)
        .select("id")
        .eq("patient_id", patient_id)
        .eq("medication", _MEDICATION)
        .limit(1)
        .execute()
    )
    return bool(result.data)


async def seed() -> None:
    random.seed(42)  # reproducible across runs
    client = await get_supabase_client()

    patient_id = await _resolve_patient_id(client)
    await _ensure_schedule(client, patient_id)

    if await _already_seeded(client, patient_id):
        print("Adherence data already present — skipping.")
        return

    today = date.today()
    rows: list[dict] = []

    for day_offset in range(_DAYS, 0, -1):
        day = today - timedelta(days=day_offset)
        for dose_time, meal_context in _DOSES:
            scheduled_at = datetime.combine(day, dose_time, tzinfo=UTC)
            taken = random.random() < _ADHERENCE_RATE
            confirmed_at = (
                (scheduled_at + timedelta(minutes=random.randint(2, 30))).isoformat()
                if taken
                else None
            )
            rows.append(
                {
                    "id": str(uuid4()),
                    "patient_id": patient_id,
                    "medication": _MEDICATION,
                    "scheduled_at": scheduled_at.isoformat(),
                    "taken": taken,
                    "meal_context": meal_context,
                    "confirmed_at": confirmed_at,
                }
            )

    await client.table(_LOG_TABLE).insert(rows).execute()

    taken_count = sum(1 for r in rows if r["taken"])
    print(
        f"Inserted {len(rows)} log entries — "
        f"{taken_count} taken / {len(rows) - taken_count} missed "
        f"({taken_count / len(rows) * 100:.1f}% adherence)"
    )
    print(f"\nTest the endpoint:")
    print(f"  GET /api/v1/adherence/{patient_id}?days=30")


if __name__ == "__main__":
    asyncio.run(seed())
