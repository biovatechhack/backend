from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from src.infrastructure.database import Base, SessionFactory, engine
from src.infrastructure.database.models import (
    ConversationLogModel,
    ConversationTurnModel,
    FamilyMemberModel,
    MedicationLogModel,
    PatientModel,
    RiskEventModel,
)


async def seed() -> None:
    """Create a demo patient and linked demo events from the architecture spec."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with SessionFactory() as session:
        existing_patient = await session.scalar(
            select(PatientModel).where(PatientModel.doctor_email == "dr.hassan@clinique.dz")
        )
        if existing_patient is not None:
            return

        now = datetime.now(UTC)
        patient = PatientModel(
            display_name="Nadia Benali",
            age=62,
            bmi=28.4,
            hba1c_last=8.1,
            baseline_glucose=126,
            medications=["Metformin 500mg", "Glipizide 5mg"],
            comorbidities=["hypertension", "type2_diabetes"],
            doctor_email="dr.hassan@clinique.dz",
        )
        patient.family_members.extend(
            [
                FamilyMemberModel(
                    name="Yacine Benali",
                    relationship="son",
                    phone_whatsapp="+213550000010",
                    alert_preferences=["push", "sms"],
                    dashboard_access="full",
                ),
                FamilyMemberModel(
                    name="Samira Benali",
                    relationship="daughter",
                    phone_whatsapp="+213550000011",
                    alert_preferences=["push"],
                    dashboard_access="full",
                ),
            ]
        )
        patient.medication_logs.extend(
            [
                MedicationLogModel(
                    medication="Metformin 500mg",
                    scheduled_at=now - timedelta(hours=8),
                    taken=True,
                    meal_context="after_meal",
                    confirmed_at=now - timedelta(hours=7, minutes=50),
                ),
                MedicationLogModel(
                    medication="Glipizide 5mg",
                    scheduled_at=now - timedelta(hours=2),
                    taken=False,
                    meal_context="before_meal",
                    confirmed_at=None,
                ),
            ]
        )

        conversation_log = ConversationLogModel(
            final_risk="HIGH",
            duration_seconds=47,
            gemini_calls=2,
            pii_stripped=True,
            created_at=now,
        )
        conversation_log.turns.extend(
            [
                ConversationTurnModel(
                    role="patient",
                    content_darija="حاسس بدوخة و عطشان بزاف",
                    turn_timestamp=now - timedelta(seconds=47),
                ),
                ConversationTurnModel(
                    role="nour",
                    content_darija="لازم تقيس السكر دابا ونبقاو معاك خطوة بخطوة.",
                    risk_at_turn="MODERATE",
                    turn_timestamp=now - timedelta(seconds=20),
                ),
            ]
        )
        patient.conversation_logs.append(conversation_log)
        patient.risk_events.append(
            RiskEventModel(
                conversation_log=conversation_log,
                risk_level="HIGH",
                confidence=0.91,
                extracted_symptoms=["dizziness", "excessive_thirst"],
                glucose_reading=58,
                top_decision_features=["glucose_deviation_pct", "symptom_severity_score"],
                biometric_passed=False,
                alerts_sent=["fcm_family", "sms_family", "email_doctor"],
                timestamp=now,
            )
        )

        session.add(patient)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
