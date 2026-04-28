from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.domain.entities import (
    ConversationLog,
    ConversationTurn,
    FamilyMember,
    MedicationLog,
    Patient,
    RiskEvent,
)

# ── Patient ───────────────────────────────────────────────────────────────────

def test_patient_requires_persisted_fields() -> None:
    created_at = datetime.now(UTC)

    patient = Patient(
        id="patient-1",
        display_name="Nadia Benali",
        age=62,
        bmi=28.4,
        hba1c_last=8.1,
        baseline_glucose=126,
        doctor_email="dr.hassan@clinique.dz",
        created_at=created_at,
    )

    assert patient.id == "patient-1"
    assert patient.created_at is created_at
    assert patient.family_members == []
    assert patient.conversation_logs == []
    assert patient.risk_events == []


def test_patient_collection_defaults_are_independent() -> None:
    """Each Patient instance gets its own list — not a shared mutable default."""
    created_at = datetime.now(UTC)
    p1 = Patient(id="a", display_name="A", age=50, bmi=22.0, hba1c_last=6.0,
                 baseline_glucose=100, doctor_email="a@b.com", created_at=created_at)
    p2 = Patient(id="b", display_name="B", age=50, bmi=22.0, hba1c_last=6.0,
                 baseline_glucose=100, doctor_email="c@d.com", created_at=created_at)

    p1.medications.append("Metformin 500mg")
    assert p2.medications == [], "mutable default was shared between instances"


def test_patient_slots_prevents_arbitrary_attributes() -> None:
    """slots=True means no __dict__; unknown attributes raise AttributeError."""
    created_at = datetime.now(UTC)
    patient = Patient(id="x", display_name="X", age=40, bmi=20.0, hba1c_last=5.5,
                      baseline_glucose=90, doctor_email="x@y.com", created_at=created_at)

    with pytest.raises(AttributeError):
        patient.nonexistent_field = "oops"  # type: ignore[attr-defined]


# ── FamilyMember ──────────────────────────────────────────────────────────────

def test_family_member_default_dashboard_access_is_full() -> None:
    member = FamilyMember(
        id="fam-1",
        patient_id="patient-1",
        name="Yacine Benali",
        relationship="son",
        phone_whatsapp="+213550000010",
        created_at=datetime.now(UTC),
    )

    assert member.dashboard_access == "full"


def test_family_member_alert_preferences_default_is_empty_list() -> None:
    member = FamilyMember(
        id="fam-2",
        patient_id="patient-1",
        name="Samira Benali",
        relationship="daughter",
        phone_whatsapp="+213550000011",
        created_at=datetime.now(UTC),
    )

    assert member.alert_preferences == []


# ── ConversationTurn ──────────────────────────────────────────────────────────

def test_conversation_turn_risk_at_turn_defaults_to_none() -> None:
    turn = ConversationTurn(
        id="turn-1",
        conversation_log_id="log-1",
        role="patient",
        content_darija="حاسس بدوخة",
        turn_timestamp=datetime.now(UTC),
    )

    assert turn.risk_at_turn is None


def test_conversation_turn_role_values() -> None:
    ts = datetime.now(UTC)
    patient_turn = ConversationTurn(
        id="t1", conversation_log_id="l1", role="patient",
        content_darija="عطشان", turn_timestamp=ts,
    )
    nour_turn = ConversationTurn(
        id="t2", conversation_log_id="l1", role="nour",
        content_darija="قيس السكر", turn_timestamp=ts, risk_at_turn="MODERATE",
    )

    assert patient_turn.role == "patient"
    assert nour_turn.risk_at_turn == "MODERATE"


# ── ConversationLog ───────────────────────────────────────────────────────────

def test_conversation_log_owns_turns_and_risk_events() -> None:
    created_at = datetime.now(UTC)
    turn = ConversationTurn(
        id="turn-1",
        conversation_log_id="log-1",
        role="patient",
        content_darija="حاسس بدوخة",
        turn_timestamp=created_at,
    )
    risk_event = RiskEvent(
        id="event-1",
        patient_id="patient-1",
        conversation_log_id="log-1",
        risk_level="HIGH",
        confidence=0.91,
        timestamp=created_at,
        extracted_symptoms=["dizziness", "excessive_thirst"],
        top_decision_features=["glucose_deviation_pct", "symptom_severity_score"],
        alerts_sent=["fcm_family", "sms_family", "email_doctor"],
    )

    conversation_log = ConversationLog(
        id="log-1",
        patient_id="patient-1",
        final_risk="HIGH",
        duration_seconds=47,
        gemini_calls=2,
        pii_stripped=True,
        created_at=created_at,
        turns=[turn],
        risk_events=[risk_event],
    )

    assert conversation_log.turns == [turn]
    assert conversation_log.risk_events == [risk_event]
    assert conversation_log.risk_events[0].conversation_log_id == conversation_log.id


def test_conversation_log_pii_stripped_flag() -> None:
    ts = datetime.now(UTC)
    log = ConversationLog(id="l1", patient_id="p1", final_risk="LOW",
                          duration_seconds=10, gemini_calls=2,
                          pii_stripped=True, created_at=ts)

    assert log.pii_stripped is True


# ── RiskEvent ─────────────────────────────────────────────────────────────────

def test_risk_event_default_field_values() -> None:
    ts = datetime.now(UTC)
    event = RiskEvent(
        id="evt-1",
        patient_id="patient-1",
        conversation_log_id="log-1",
        risk_level="LOW",
        confidence=0.75,
        timestamp=ts,
    )

    assert event.extracted_symptoms == []
    assert event.glucose_reading is None
    assert event.top_decision_features == []
    assert event.biometric_passed is False
    assert event.alerts_sent == []


def test_risk_event_high_risk_with_all_alerts() -> None:
    ts = datetime.now(UTC)
    event = RiskEvent(
        id="evt-2",
        patient_id="patient-1",
        conversation_log_id="log-1",
        risk_level="HIGH",
        confidence=0.91,
        timestamp=ts,
        extracted_symptoms=["dizziness", "excessive_thirst"],
        glucose_reading=58.0,
        top_decision_features=["glucose_deviation_pct", "symptom_severity_score"],
        biometric_passed=False,
        alerts_sent=["fcm_family", "sms_family", "email_doctor"],
    )

    assert event.risk_level == "HIGH"
    assert len(event.alerts_sent) == 3
    assert event.glucose_reading == pytest.approx(58.0)


# ── MedicationLog ─────────────────────────────────────────────────────────────

def test_medication_log_optional_confirmed_at() -> None:
    ts = datetime.now(UTC)
    log = MedicationLog(
        id="med-1",
        patient_id="patient-1",
        medication="Glipizide 5mg",
        scheduled_at=ts,
        taken=False,
        meal_context="before_meal",
    )

    assert log.confirmed_at is None
    assert log.taken is False


def test_medication_log_confirmed_taken() -> None:
    ts = datetime.now(UTC)
    log = MedicationLog(
        id="med-2",
        patient_id="patient-1",
        medication="Metformin 500mg",
        scheduled_at=ts,
        taken=True,
        meal_context="after_meal",
        confirmed_at=ts,
    )

    assert log.taken is True
    assert log.confirmed_at is ts


# ── Fixture contract tests ────────────────────────────────────────────────────

def test_demo_patient_fixture_matches_domain_contract(demo_patient: dict) -> None:
    required_keys = {
        "id",
        "display_name",
        "age",
        "bmi",
        "hba1c_last",
        "baseline_glucose",
        "doctor_email",
        "created_at",
        "family_members",
    }

    assert required_keys.issubset(demo_patient)
    assert demo_patient["display_name"] == "Nadia Benali"
    assert demo_patient["family_members"][0]["patient_id"] == demo_patient["id"]


def test_persisted_related_entities_require_parent_ids() -> None:
    created_at = datetime.now(UTC)

    family_member = FamilyMember(
        id="family-1",
        patient_id="patient-1",
        name="Yacine Benali",
        relationship="son",
        phone_whatsapp="+213550000010",
        created_at=created_at,
    )
    medication_log = MedicationLog(
        id="med-1",
        patient_id="patient-1",
        medication="Metformin 500mg",
        scheduled_at=created_at,
        taken=True,
        meal_context="after_meal",
        confirmed_at=created_at,
    )

    assert family_member.patient_id == "patient-1"
    assert medication_log.patient_id == "patient-1"


def test_mock_gemini_client_fixture_is_faithful(
    mock_gemini_client, mock_gemini_extraction: dict, mock_gemini_response_high: str
) -> None:
    assert mock_gemini_client.extract_entities.return_value == mock_gemini_extraction
    assert mock_gemini_client.generate_response.return_value == mock_gemini_response_high
