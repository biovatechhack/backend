from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.base import Base
from src.infrastructure.database.models import (
    ConversationLogModel,
    ConversationTurnModel,
    FamilyMemberModel,
    MedicationLogModel,
    PatientModel,
    RiskEventModel,
)

# ── In-memory engine shared across session tests ──────────────────────────────

@pytest.fixture
async def db_session() -> AsyncSession:
    """Isolated in-memory SQLite for each test — no shared state."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session

    await engine.dispose()


# ── Helper builders ───────────────────────────────────────────────────────────

def _make_patient(**kwargs) -> PatientModel:
    defaults = dict(
        display_name="Nadia Benali",
        age=62,
        bmi=28.4,
        hba1c_last=8.1,
        baseline_glucose=126.0,
        medications=["Metformin 500mg", "Glipizide 5mg"],
        comorbidities=["hypertension", "type2_diabetes"],
        doctor_email="dr.hassan@clinique.dz",
    )
    defaults.update(kwargs)
    return PatientModel(**defaults)


# ── Basic CRUD ────────────────────────────────────────────────────────────────

async def test_insert_and_retrieve_patient(db_session: AsyncSession) -> None:
    patient = _make_patient()
    db_session.add(patient)
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.scalar(select(PatientModel).where(
        PatientModel.doctor_email == "dr.hassan@clinique.dz"
    ))

    assert result is not None
    assert result.display_name == "Nadia Benali"
    assert result.age == 62


async def test_patient_id_auto_generated_as_uuid(db_session: AsyncSession) -> None:
    patient = _make_patient()
    db_session.add(patient)
    await db_session.commit()

    assert patient.id is not None
    assert len(patient.id) == 36  # UUID4 format: 8-4-4-4-12


async def test_patient_created_at_auto_generated(db_session: AsyncSession) -> None:
    patient = _make_patient()
    db_session.add(patient)
    await db_session.commit()

    assert isinstance(patient.created_at, datetime)


async def test_json_columns_round_trip(db_session: AsyncSession) -> None:
    """medications and comorbidities survive a write/read cycle as lists."""
    patient = _make_patient(
        medications=["Insulin Glargine 10U", "Metformin 500mg"],
        comorbidities=["type2_diabetes"],
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    assert patient.medications == ["Insulin Glargine 10U", "Metformin 500mg"]
    assert patient.comorbidities == ["type2_diabetes"]


# ── Relationship traversal ────────────────────────────────────────────────────

async def test_family_member_linked_to_patient(db_session: AsyncSession) -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    patient = _make_patient()
    member = FamilyMemberModel(
        name="Yacine Benali",
        relationship="son",
        phone_whatsapp="+213550000010",
        alert_preferences=["push", "sms"],
        dashboard_access="full",
    )
    patient.family_members.append(member)
    db_session.add(patient)
    await db_session.commit()

    loaded = await db_session.scalar(
        select(PatientModel)
        .options(selectinload(PatientModel.family_members))
        .where(PatientModel.id == patient.id)
    )
    assert loaded is not None
    assert len(loaded.family_members) == 1
    assert loaded.family_members[0].name == "Yacine Benali"
    assert loaded.family_members[0].patient_id == patient.id


async def test_conversation_log_with_turns(db_session: AsyncSession) -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    now = datetime.now(UTC)
    patient = _make_patient()
    log = ConversationLogModel(
        final_risk="HIGH",
        duration_seconds=47,
        gemini_calls=2,
        pii_stripped=True,
        created_at=now,
    )
    log.turns.extend([
        ConversationTurnModel(
            role="patient",
            content_darija="حاسس بدوخة",
            turn_timestamp=now,
        ),
        ConversationTurnModel(
            role="nour",
            content_darija="قيس السكر",
            risk_at_turn="MODERATE",
            turn_timestamp=now,
        ),
    ])
    patient.conversation_logs.append(log)
    db_session.add(patient)
    await db_session.commit()

    loaded_log = await db_session.scalar(
        select(ConversationLogModel)
        .options(selectinload(ConversationLogModel.turns))
        .where(ConversationLogModel.id == log.id)
    )
    assert loaded_log is not None
    assert len(loaded_log.turns) == 2
    nour_turn = next(t for t in loaded_log.turns if t.role == "nour")
    assert nour_turn.risk_at_turn == "MODERATE"


async def test_risk_event_linked_to_patient_and_log(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    patient = _make_patient()
    log = ConversationLogModel(
        final_risk="HIGH", duration_seconds=47, gemini_calls=2,
        pii_stripped=True, created_at=now,
    )
    event = RiskEventModel(
        conversation_log=log,
        risk_level="HIGH",
        confidence=0.91,
        extracted_symptoms=["dizziness", "excessive_thirst"],
        glucose_reading=58.0,
        top_decision_features=["glucose_deviation_pct"],
        biometric_passed=False,
        alerts_sent=["fcm_family", "sms_family", "email_doctor"],
        timestamp=now,
    )
    patient.conversation_logs.append(log)
    patient.risk_events.append(event)
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.patient_id == patient.id
    assert event.conversation_log_id == log.id
    assert event.glucose_reading == pytest.approx(58.0)


# ── Cascade delete ────────────────────────────────────────────────────────────

async def test_deleting_patient_cascades_to_family_members(db_session: AsyncSession) -> None:
    from sqlalchemy import select

    patient = _make_patient()
    patient.family_members.append(FamilyMemberModel(
        name="Yacine Benali",
        relationship="son",
        phone_whatsapp="+213550000010",
        alert_preferences=[],
        dashboard_access="full",
    ))
    db_session.add(patient)
    await db_session.commit()

    await db_session.delete(patient)
    await db_session.commit()

    remaining = await db_session.scalars(select(FamilyMemberModel))
    assert list(remaining) == []


async def test_deleting_patient_cascades_to_medication_logs(db_session: AsyncSession) -> None:
    from sqlalchemy import select

    now = datetime.now(UTC)
    patient = _make_patient()
    patient.medication_logs.append(MedicationLogModel(
        medication="Metformin 500mg",
        scheduled_at=now,
        taken=True,
        meal_context="after_meal",
    ))
    db_session.add(patient)
    await db_session.commit()

    await db_session.delete(patient)
    await db_session.commit()

    remaining = await db_session.scalars(select(MedicationLogModel))
    assert list(remaining) == []
