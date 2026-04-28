from __future__ import annotations

import logging
from typing import Any, cast

from supabase import AsyncClient, acreate_client

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None


async def get_supabase_client() -> AsyncClient:
    """Return the shared AsyncClient, initialising it on first call."""
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set before using SupabaseClient"
            )
        _client = await acreate_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _client


class SupabaseClient:
    """Async Supabase wrapper for backend persistence operations.

    Flutter clients read directly via the Supabase JS/Dart SDK.
    All writes must go through this class using the service-role key.
    """

    async def upsert_row(self, table: str, row: dict[str, Any]) -> None:
        """Insert or update a row. Uses ON CONFLICT DO UPDATE semantics."""
        logger.info("supabase.upsert table=%s", table)
        client = await get_supabase_client()
        await client.table(table).upsert(row).execute()

    async def get_row(
        self, table: str, match: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Fetch a single row matching all key-value pairs. Returns None if not found."""
        client = await get_supabase_client()
        query = client.table(table).select("*")
        for col, val in match.items():
            query = query.eq(col, val)
        result = await query.limit(1).execute()
        return cast(dict[str, Any], result.data[0]) if result.data else None
