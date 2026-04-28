from __future__ import annotations

import logging

from abstraction.repositories.risk_event_repository_port import RiskEventRepositoryPort
from domain.entities.risk_event import RiskEvent
from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)


def _event_to_row(event: RiskEvent) -> dict:
    return {
        "id": event.id,
        "patient_id": event.patient_id,
        "conversation_log_id": event.conversation_log_id,
        "risk_level": event.risk_level,
        "confidence": event.confidence,
        "extracted_symptoms": event.extracted_symptoms,
        "glucose_reading": event.glucose_reading,
        "top_decision_features": event.top_decision_features,
        "biometric_passed": event.biometric_passed,
        "alerts_sent": event.alerts_sent,
        "timestamp": event.timestamp.isoformat(),
    }


class SupabaseRiskEventRepository(RiskEventRepositoryPort):
    async def save(self, event: RiskEvent) -> str:
        client = await get_supabase_client()
        await client.table("risk_events").insert(_event_to_row(event)).execute()
        logger.info("risk_event saved id=%s level=%s", event.id, event.risk_level)
        return event.id

    async def update_alerts_sent(self, event_id: str, channels: list[str]) -> None:
        client = await get_supabase_client()
        await (
            client.table("risk_events")
            .update({"alerts_sent": channels})
            .eq("id", event_id)
            .execute()
        )
        logger.info("risk_event alerts_sent updated id=%s channels=%s", event_id, channels)
