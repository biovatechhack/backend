"""
Supabase implementation of DoctorRepository.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from abstraction.repositories.doctor_repository import DoctorRepositoryPort
from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)

TABLE = "doctors"


class SupabaseDoctorRepository(DoctorRepositoryPort):

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        client = await get_supabase_client()
        result = await client.table(TABLE).insert(row).execute()
        
        if not result.data:
            raise RuntimeError("Failed to insert doctor.")
            
        return result.data[0]

    async def get_by_id(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        client = await get_supabase_client()
        result = (
            await client
            .table(TABLE)
            .select("*")
            .eq("id", doctor_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def list_all(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
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

    async def update(self, doctor_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Strip None values
        patch = {k: v for k, v in data.items() if v is not None}
        if not patch:
            return await self.get_by_id(doctor_id)

        client = await get_supabase_client()
        result = (
            await client
            .table(TABLE)
            .update(patch)
            .eq("id", doctor_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def delete(self, doctor_id: str) -> bool:
        client = await get_supabase_client()
        result = await client.table(TABLE).delete().eq("id", doctor_id).execute()
        # Supabase delete doesn't return data if nothing deleted, check if count or existing
        return True
