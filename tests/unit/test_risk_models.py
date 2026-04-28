from __future__ import annotations

import pytest

from src.domain.models.risk_models import RiskFeatures, RiskPrediction


# ── RiskFeatures ──────────────────────────────────────────────────────────────

def test_risk_features_required_fields() -> None:
    f = RiskFeatures(age=55, bmi=28.0, hba1c_last=7.5, baseline_glucose=8.0)
    assert f.age == 55
    assert f.bmi == 28.0


def test_risk_features_optional_defaults() -> None:
    f = RiskFeatures(age=55, bmi=28.0, hba1c_last=7.5, baseline_glucose=8.0)
    assert f.current_glucose is None
    assert f.symptom_count == 0
    assert f.has_hypertension is False
    assert f.has_heart_disease is False
    assert f.medication_count == 0


def test_risk_features_with_all_fields() -> None:
    f = RiskFeatures(
        age=70,
        bmi=35.5,
        hba1c_last=10.2,
        baseline_glucose=12.0,
        current_glucose=14.0,
        symptom_count=4,
        has_hypertension=True,
        has_heart_disease=True,
        medication_count=3,
    )
    assert f.current_glucose == 14.0
    assert f.has_hypertension is True


# ── RiskPrediction ────────────────────────────────────────────────────────────

def test_risk_prediction_valid_levels() -> None:
    for level in ("low", "medium", "high"):
        p = RiskPrediction(risk_level=level, confidence=0.85)
        assert p.risk_level == level


def test_risk_prediction_confidence_bounds() -> None:
    p = RiskPrediction(risk_level="high", confidence=1.0)
    assert p.confidence == 1.0
    with pytest.raises(Exception):
        RiskPrediction(risk_level="high", confidence=1.1)
    with pytest.raises(Exception):
        RiskPrediction(risk_level="high", confidence=-0.1)


def test_risk_prediction_top_features_default_empty() -> None:
    p = RiskPrediction(risk_level="low", confidence=0.9)
    assert p.top_features == []


def test_risk_prediction_top_features_populated() -> None:
    p = RiskPrediction(
        risk_level="high",
        confidence=0.92,
        top_features=["hba1c_last", "current_glucose", "bmi"],
    )
    assert "hba1c_last" in p.top_features
