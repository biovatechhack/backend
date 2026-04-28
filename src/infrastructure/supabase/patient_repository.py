Concrete implementation of PatientRepository using the Supabase async client.

All writes use the service-role key (bypasses RLS).
All reads return plain dicts — mapping to domain entities happens in the
use case layer if needed.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from abstraction.repositories.patient_repository import PatientRepository
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from abstraction.repositories.patient_repository_port import PatientRepositoryPort
from domain.entities.family_member import FamilyMember
from domain.entities.patient import Patient
from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _row_to_family_member(row: dict[str, Any]) -> FamilyMember:
    return FamilyMember(
        id=row["id"],
        patient_id=row["patient_id"],
        name=row["name"],
        relationship=row["relationship"],
        phone_whatsapp=row["phone_whatsapp"],
        alert_preferences=row.get("alert_preferences") or [],
        dashboard_access=row.get("dashboard_access", "full"),
        created_at=_parse_dt(row.get("created_at")),
    )


def _row_to_patient(row: dict[str, Any]) -> Patient:
    return Patient(
        id=row["id"],
        display_name=row["display_name"],
        age=int(row["age"]),
        gender=row["gender"],
        bmi=float(row["bmi"]),
        hba1c_last=float(row["hba1c_last"]),
        baseline_glucose=float(row["baseline_glucose"]),
        doctor_email=row["doctor_email"],
        medications=row.get("medications") or [],
        comorbidities=row.get("comorbidities") or [],
        created_at=_parse_dt(row.get("created_at")),
    )


class SupabasePatientRepository(PatientRepositoryPort):
    async def get_by_id(self, patient_id: str) -> Patient | None:
        client = await get_supabase_client()
        result = (
            await client.table("patients")
            .select("*")
            .eq("id", patient_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            logger.debug("patient not found: %s", patient_id)
            return None
        return _row_to_patient(result.data[0])

    async def get_with_family(self, patient_id: str) -> Patient | None:
        patient = await self.get_by_id(patient_id)
        if patient is None:
            return None
        client = await get_supabase_client()
        fm_result = (
            await client.table("family_members")
            .select("*")
            .eq("patient_id", patient_id)
            .execute()
        )
        patient.family_members = [_row_to_family_member(r) for r in fm_result.data]
        return patient
