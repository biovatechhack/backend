"""
SupabasePatientRepository
=========================
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
from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "patients"


class SupabasePatientRepository(PatientRepository):
    """Supabase-backed CRUD for the `patients` table."""

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new patient row.
        Generates id and created_at server-side so callers don't have to.
        """
        row = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        client = await get_supabase_client()
        result = await client.table(TABLE).insert(row).execute()

        if not result.data:
            raise RuntimeError("Failed to insert patient — Supabase returned no data.")

        logger.info("[PatientRepo] created patient id=%s", row["id"])
        return result.data[0]

    # ── Read (single) ─────────────────────────────────────────────────────────

    async def get_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Return one patient row or None."""
        client = await get_supabase_client()
        result = (
            await client
            .table(TABLE)
            .select("*")
            .eq("id", patient_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ── Read (list) ───────────────────────────────────────────────────────────

    async def list_all(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Return a paginated list of patient rows."""
        client = await get_supabase_client()
        result = (
            await client
            .table(TABLE)
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or []

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(self, patient_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Patch only the provided fields.
        Returns the updated row, or None if the patient doesn't exist.
        """
        # Verify existence first to give a clear 404
        existing = await self.get_by_id(patient_id)
        if existing is None:
            return None

        # Strip None values — don't overwrite existing data with nulls
        patch = {k: v for k, v in data.items() if v is not None}
        if not patch:
            return existing   # nothing to update

        client = await get_supabase_client()
        result = (
            await client
            .table(TABLE)
            .update(patch)
            .eq("id", patient_id)
            .execute()
        )

        logger.info("[PatientRepo] updated patient id=%s fields=%s", patient_id, list(patch))
        return result.data[0] if result.data else existing

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete(self, patient_id: str) -> bool:
        """
        Delete a patient by id.
        Returns True if found and deleted, False if not found.
        """
        existing = await self.get_by_id(patient_id)
        if existing is None:
            return False

        client = await get_supabase_client()
        await client.table(TABLE).delete().eq("id", patient_id).execute()

        logger.info("[PatientRepo] deleted patient id=%s", patient_id)
        return True
