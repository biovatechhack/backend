from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.base import Base
from src.infrastructure.database.models import (
    ConversationLogModel,
    FamilyMemberModel,
    MedicationLogModel,
    PatientModel,
    RiskEventModel,
)


@pytest.fixture
async def seeded_session() -> AsyncSession:
    """Run the seed script against an in-memory DB and yield the open session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    # Patch settings so the seed uses this engine, not the file-based default.
    import scripts.seed_demo_data as seed_module

    original_engine = seed_module.engine
    original_factory = seed_module.SessionFactory
    seed_module.engine = engine
    seed_module.SessionFactory = factory

    await seed_module.seed()

    seed_module.engine = original_engine
    seed_module.SessionFactory = original_factory

    async with factory() as session:
        yield session

    await engine.dispose()


# ── Demo patient existence ────────────────────────────────────────────────────

async def test_seed_creates_demo_patient(seeded_session: AsyncSession) -> None:
    patient = await seeded_session.scalar(
        select(PatientModel).where(PatientModel.doctor_email == "dr.hassan@clinique.dz")
    )

    assert patient is not None
    assert patient.display_name == "Nadia Benali"
    assert patient.age == 62
    assert patient.bmi == pytest.approx(28.4)
    assert patient.hba1c_last == pytest.approx(8.1)
    assert patient.baseline_glucose == pytest.approx(126.0)


async def test_demo_patient_medications_match_spec(seeded_session: AsyncSession) -> None:
    patient = await seeded_session.scalar(
        select(PatientModel).where(PatientModel.doctor_email == "dr.hassan@clinique.dz")
    )
    assert patient is not None
    assert "Metformin 500mg" in patient.medications
    assert "Glipizide 5mg" in patient.medications


async def test_demo_patient_comorbidities_match_spec(seeded_session: AsyncSession) -> None:
    patient = await seeded_session.scalar(
        select(PatientModel).where(PatientModel.doctor_email == "dr.hassan@clinique.dz")
    )
    assert patient is not None
    assert "hypertension" in patient.comorbidities
    assert "type2_diabetes" in patient.comorbidities


# ── Family members ────────────────────────────────────────────────────────────

async def test_demo_patient_has_two_family_members(seeded_session: AsyncSession) -> None:
    patient = await seeded_session.scalar(
        select(PatientModel).where(PatientModel.doctor_email == "dr.hassan@clinique.dz")
    )
    assert patient is not None
    members = list(await seeded_session.scalars(
        select(FamilyMemberModel).where(FamilyMemberModel.patient_id == patient.id)
    ))

    assert len(members) == 2
    names = {m.name for m in members}
    assert names == {"Yacine Benali", "Samira Benali"}


async def test_demo_family_member_relationships(seeded_session: AsyncSession) -> None:
    members = list(await seeded_session.scalars(select(FamilyMemberModel)))

    relationships = {m.relationship for m in members}
    assert relationships == {"son", "daughter"}


# ── Medication logs ───────────────────────────────────────────────────────────

async def test_demo_patient_has_two_medication_logs(seeded_session: AsyncSession) -> None:
    patient = await seeded_session.scalar(
        select(PatientModel).where(PatientModel.doctor_email == "dr.hassan@clinique.dz")
    )
    assert patient is not None
    logs = list(await seeded_session.scalars(
        select(MedicationLogModel).where(MedicationLogModel.patient_id == patient.id)
    ))

    assert len(logs) == 2


async def test_demo_medication_logs_have_correct_taken_flags(seeded_session: AsyncSession) -> None:
    logs = {m.medication: m for m in await seeded_session.scalars(select(MedicationLogModel))}

    assert logs["Metformin 500mg"].taken is True
    assert logs["Glipizide 5mg"].taken is False
    assert logs["Glipizide 5mg"].confirmed_at is None


# ── Conversation log + turns ──────────────────────────────────────────────────

async def test_demo_patient_has_one_conversation_log(seeded_session: AsyncSession) -> None:
    patient = await seeded_session.scalar(
        select(PatientModel).where(PatientModel.doctor_email == "dr.hassan@clinique.dz")
    )
    assert patient is not None
    logs = list(await seeded_session.scalars(
        select(ConversationLogModel).where(ConversationLogModel.patient_id == patient.id)
    ))

    assert len(logs) == 1
    assert logs[0].final_risk == "HIGH"
    assert logs[0].gemini_calls == 2
    assert logs[0].pii_stripped is True


async def test_demo_conversation_log_has_two_turns(seeded_session: AsyncSession) -> None:
    from src.infrastructure.database.models import ConversationTurnModel

    log = await seeded_session.scalar(select(ConversationLogModel))
    assert log is not None

    turns = list(await seeded_session.scalars(
        select(ConversationTurnModel).where(
            ConversationTurnModel.conversation_log_id == log.id
        )
    ))

    assert len(turns) == 2
    roles = {t.role for t in turns}
    assert roles == {"patient", "nour"}


# ── Risk event ────────────────────────────────────────────────────────────────

async def test_demo_patient_has_one_risk_event(seeded_session: AsyncSession) -> None:
    patient = await seeded_session.scalar(
        select(PatientModel).where(PatientModel.doctor_email == "dr.hassan@clinique.dz")
    )
    assert patient is not None
    events = list(await seeded_session.scalars(
        select(RiskEventModel).where(RiskEventModel.patient_id == patient.id)
    ))

    assert len(events) == 1
    event = events[0]
    assert event.risk_level == "HIGH"
    assert event.confidence == pytest.approx(0.91)
    assert event.glucose_reading == pytest.approx(58.0)
    assert "fcm_family" in event.alerts_sent
    assert "sms_family" in event.alerts_sent
    assert "email_doctor" in event.alerts_sent


# ── Idempotency ───────────────────────────────────────────────────────────────

async def test_seed_is_idempotent(seeded_session: AsyncSession) -> None:
    """Running seed() a second time must not create duplicate patients."""
    import scripts.seed_demo_data as seed_module

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    original_engine = seed_module.engine
    original_factory = seed_module.SessionFactory
    seed_module.engine = engine
    seed_module.SessionFactory = factory

    await seed_module.seed()
    await seed_module.seed()  # second run

    seed_module.engine = original_engine
    seed_module.SessionFactory = original_factory

    async with factory() as session:
        all_patients = list(await session.scalars(select(PatientModel)))

    await engine.dispose()

    assert len(all_patients) == 1, "seed() must not insert a duplicate patient on second run"
