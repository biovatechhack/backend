from __future__ import annotations

import logging
from datetime import UTC, datetime

from abstraction.repositories.risk_event_repository_port import RiskEventRepositoryPort
from domain.entities.risk_event import RiskEvent
from infrastructure.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)


def _row_to_event(row: dict) -> RiskEvent:
    ts = datetime.fromisoformat(row["timestamp"])
    return RiskEvent(
        id=row["id"],
        patient_id=row["patient_id"],
        conversation_log_id=row["conversation_log_id"],
        risk_level=row["risk_level"],
        confidence=float(row["confidence"]),
        timestamp=ts if ts.tzinfo else ts.replace(tzinfo=UTC),
        extracted_symptoms=row.get("extracted_symptoms") or [],
        glucose_reading=row.get("glucose_reading"),
        top_decision_features=row.get("top_decision_features") or [],
        biometric_passed=bool(row.get("biometric_passed", False)),
        alerts_sent=row.get("alerts_sent") or [],
    )


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

    async def get_by_patient_since(
        self, patient_id: str, since: datetime
    ) -> list[RiskEvent]:
        client = await get_supabase_client()
        result = (
            await client.table("risk_events")
            .select("*")
            .eq("patient_id", patient_id)
            .gte("timestamp", since.isoformat())
            .order("timestamp", desc=True)
            .execute()
        )
        return [_row_to_event(r) for r in result.data]
