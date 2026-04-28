from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as sa_relationship

from infrastructure.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PatientModel(Base):
    """SQLAlchemy persistence model for patient profiles."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    display_name: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column(Integer())
    bmi: Mapped[float] = mapped_column(Float())
    hba1c_last: Mapped[float] = mapped_column(Float())
    baseline_glucose: Mapped[float] = mapped_column(Float())
    medications: Mapped[list[str]] = mapped_column(JSON())
    comorbidities: Mapped[list[str]] = mapped_column(JSON())
    doctor_email: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    family_members: Mapped[list[FamilyMemberModel]] = sa_relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    medication_logs: Mapped[list[MedicationLogModel]] = sa_relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    conversation_logs: Mapped[list[ConversationLogModel]] = sa_relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    risk_events: Mapped[list[RiskEventModel]] = sa_relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )


class ConversationLogModel(Base):
    """SQLAlchemy persistence model for patient conversation sessions."""

    __tablename__ = "conversation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    final_risk: Mapped[str] = mapped_column(String(16))
    duration_seconds: Mapped[int] = mapped_column(Integer())
    gemini_calls: Mapped[int] = mapped_column(Integer())
    pii_stripped: Mapped[bool] = mapped_column(Boolean(), default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    patient: Mapped[PatientModel] = sa_relationship(back_populates="conversation_logs")
    turns: Mapped[list[ConversationTurnModel]] = sa_relationship(
        back_populates="conversation_log",
        cascade="all, delete-orphan",
    )
    risk_events: Mapped[list[RiskEventModel]] = sa_relationship(back_populates="conversation_log")


class ConversationTurnModel(Base):
    """SQLAlchemy persistence model for individual conversation turns."""

    __tablename__ = "conversation_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_log_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_logs.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32))
    content_darija: Mapped[str] = mapped_column(String(1000))
    risk_at_turn: Mapped[str | None] = mapped_column(String(16), nullable=True)
    turn_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation_log: Mapped[ConversationLogModel] = sa_relationship(back_populates="turns")


class FamilyMemberModel(Base):
    """SQLAlchemy persistence model for family contacts."""

    __tablename__ = "family_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    relationship: Mapped[str] = mapped_column(String(64))
    phone_whatsapp: Mapped[str] = mapped_column(String(32))
    alert_preferences: Mapped[list[str]] = mapped_column(JSON())
    dashboard_access: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    patient: Mapped[PatientModel] = sa_relationship(back_populates="family_members")


class RiskEventModel(Base):
    """SQLAlchemy persistence model for risk scoring outputs."""

    __tablename__ = "risk_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    conversation_log_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_logs.id", ondelete="CASCADE"),
        index=True,
    )
    risk_level: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float())
    extracted_symptoms: Mapped[list[str]] = mapped_column(JSON())
    glucose_reading: Mapped[float | None] = mapped_column(Float(), nullable=True)
    top_decision_features: Mapped[list[str]] = mapped_column(JSON())
    biometric_passed: Mapped[bool] = mapped_column(Boolean(), default=False)
    alerts_sent: Mapped[list[str]] = mapped_column(JSON())
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    patient: Mapped[PatientModel] = sa_relationship(back_populates="risk_events")
    conversation_log: Mapped[ConversationLogModel] = sa_relationship(back_populates="risk_events")


class MedicationLogModel(Base):
    """SQLAlchemy persistence model for medication adherence entries."""

    __tablename__ = "medication_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    medication: Mapped[str] = mapped_column(String(120))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    taken: Mapped[bool] = mapped_column(Boolean())
    meal_context: Mapped[str] = mapped_column(String(32))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped[PatientModel] = sa_relationship(back_populates="medication_logs")
