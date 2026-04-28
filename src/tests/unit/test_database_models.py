from __future__ import annotations

import sqlalchemy as sa

from src.infrastructure.database import models  # noqa: F401
from src.infrastructure.database.base import Base
from src.infrastructure.database.models import (
    ConversationLogModel,
    ConversationTurnModel,
    FamilyMemberModel,
    MedicationLogModel,
    PatientModel,
    RiskEventModel,
)

# ── Table registration ────────────────────────────────────────────────────────

def test_expected_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "patients",
        "conversation_logs",
        "conversation_turns",
        "family_members",
        "risk_events",
        "medication_logs",
    }


# ── Column presence ───────────────────────────────────────────────────────────

def _column_names(model: type) -> set[str]:
    return {c.key for c in sa.inspect(model).mapper.column_attrs}


def test_patient_model_columns() -> None:
    cols = _column_names(PatientModel)
    assert cols == {
        "id", "display_name", "age", "bmi", "hba1c_last",
        "baseline_glucose", "medications", "comorbidities",
        "doctor_email", "created_at",
    }


def test_family_member_model_columns() -> None:
    cols = _column_names(FamilyMemberModel)
    assert cols == {
        "id", "patient_id", "name", "relationship",
        "phone_whatsapp", "alert_preferences", "dashboard_access", "created_at",
    }


def test_conversation_log_model_columns() -> None:
    cols = _column_names(ConversationLogModel)
    assert cols == {
        "id", "patient_id", "final_risk", "duration_seconds",
        "gemini_calls", "pii_stripped", "created_at",
    }


def test_conversation_turn_model_columns() -> None:
    cols = _column_names(ConversationTurnModel)
    assert cols == {
        "id", "conversation_log_id", "role",
        "content_darija", "risk_at_turn", "turn_timestamp",
    }


def test_risk_event_model_columns() -> None:
    cols = _column_names(RiskEventModel)
    assert cols == {
        "id", "patient_id", "conversation_log_id", "risk_level",
        "confidence", "extracted_symptoms", "glucose_reading",
        "top_decision_features", "biometric_passed", "alerts_sent", "timestamp",
    }


def test_medication_log_model_columns() -> None:
    cols = _column_names(MedicationLogModel)
    assert cols == {
        "id", "patient_id", "medication", "scheduled_at",
        "taken", "meal_context", "confirmed_at",
    }


# ── Relationships ─────────────────────────────────────────────────────────────

def _relationship_names(model: type) -> set[str]:
    return {r.key for r in sa.inspect(model).mapper.relationships}


def test_patient_has_all_relationships() -> None:
    rels = _relationship_names(PatientModel)
    assert rels == {"family_members", "medication_logs", "conversation_logs", "risk_events"}


def test_conversation_log_has_all_relationships() -> None:
    rels = _relationship_names(ConversationLogModel)
    assert rels == {"patient", "turns", "risk_events"}


def test_conversation_turn_back_populates_log() -> None:
    rels = _relationship_names(ConversationTurnModel)
    assert "conversation_log" in rels


def test_family_member_back_populates_patient() -> None:
    rels = _relationship_names(FamilyMemberModel)
    assert "patient" in rels


# ── Cascade delete configured ─────────────────────────────────────────────────

def test_family_members_cascade_is_delete_orphan() -> None:
    insp = sa.inspect(PatientModel)
    fm_rel = next(r for r in insp.mapper.relationships if r.key == "family_members")
    assert "delete-orphan" in fm_rel.cascade


def test_conversation_turns_cascade_is_delete_orphan() -> None:
    insp = sa.inspect(ConversationLogModel)
    turns_rel = next(r for r in insp.mapper.relationships if r.key == "turns")
    assert "delete-orphan" in turns_rel.cascade


# ── JSON columns ──────────────────────────────────────────────────────────────

def test_patient_medications_is_json_type() -> None:
    table = Base.metadata.tables["patients"]
    col = table.c["medications"]
    assert isinstance(col.type, sa.JSON)


def test_risk_event_extracted_symptoms_is_json_type() -> None:
    table = Base.metadata.tables["risk_events"]
    col = table.c["extracted_symptoms"]
    assert isinstance(col.type, sa.JSON)


# ── Nullable constraints ──────────────────────────────────────────────────────

def test_risk_at_turn_is_nullable() -> None:
    table = Base.metadata.tables["conversation_turns"]
    assert table.c["risk_at_turn"].nullable is True


def test_glucose_reading_is_nullable() -> None:
    table = Base.metadata.tables["risk_events"]
    assert table.c["glucose_reading"].nullable is True


def test_confirmed_at_is_nullable() -> None:
    table = Base.metadata.tables["medication_logs"]
    assert table.c["confirmed_at"].nullable is True


def test_patient_display_name_is_not_nullable() -> None:
    table = Base.metadata.tables["patients"]
    assert table.c["display_name"].nullable is False
