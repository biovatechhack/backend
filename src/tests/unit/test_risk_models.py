from __future__ import annotations

import pytest

from src.domain.models.risk_models import RiskFeatures, RiskPrediction


# ── RiskFeatures ──────────────────────────────────────────────────────────────

def test_risk_features_required_fields() -> None:
    f = RiskFeatures(age=55, hba1c=7.5, glucose=130.0, hr=75, spo2=97, steps=5000, sleep_hours=7.0)
    assert f.age == 55
    assert f.hba1c == 7.5
    assert f.glucose == 130.0


def test_risk_features_optional_symptom_defaults() -> None:
    f = RiskFeatures(age=55, hba1c=7.5, glucose=130.0, hr=75, spo2=97, steps=5000, sleep_hours=7.0)
    assert f.confusion is False
    assert f.tremors is False
    assert f.thirst is False


def test_risk_features_with_symptom_flags() -> None:
    f = RiskFeatures(
        age=70,
        hba1c=10.2,
        glucose=380.0,
        hr=105,
        spo2=92,
        steps=800,
        sleep_hours=5.0,
        confusion=True,
        thirst=True,
    )
    assert f.confusion is True
    assert f.thirst is True
    assert f.tremors is False


# ── RiskPrediction ────────────────────────────────────────────────────────────

def test_risk_prediction_valid_levels() -> None:
    for level in ("low", "moderate", "high"):
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


def test_risk_prediction_class_probabilities_default_empty() -> None:
    p = RiskPrediction(risk_level="low", confidence=0.9)
    assert p.class_probabilities == {}


def test_risk_prediction_feature_contributions_default_empty() -> None:
    p = RiskPrediction(risk_level="low", confidence=0.9)
    assert p.feature_contributions == {}


def test_risk_prediction_full() -> None:
    p = RiskPrediction(
        risk_level="high",
        confidence=0.92,
        top_features=["glucose", "hr", "confusion"],
        class_probabilities={"low": 0.05, "moderate": 0.03, "high": 0.92},
        feature_contributions={"glucose": 1.8, "hr": 0.6, "confusion": 0.9},
    )
    assert "glucose" in p.top_features
    assert abs(sum(p.class_probabilities.values()) - 1.0) < 1e-6
