from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.models.risk_models import RiskFeatures, RiskPrediction
from src.infrastructure.ml.risk_classifier import RISK_LABELS, RiskClassifier

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "risk_tree.pkl"


@pytest.fixture(scope="module")
def classifier() -> RiskClassifier:
    return RiskClassifier(model_path=MODEL_PATH)


# ── basic contract ────────────────────────────────────────────────────────────

def test_model_file_exists() -> None:
    assert MODEL_PATH.exists(), "models/risk_tree.pkl missing — run scripts/train_risk_tree.py"


def test_classifier_loads(classifier: RiskClassifier) -> None:
    assert classifier is not None


def test_predict_returns_risk_prediction(classifier: RiskClassifier) -> None:
    f = RiskFeatures(age=55, bmi=28.0, hba1c_last=7.5, baseline_glucose=8.0)
    result = classifier.predict(f)
    assert isinstance(result, RiskPrediction)


def test_predict_risk_level_is_valid(classifier: RiskClassifier) -> None:
    f = RiskFeatures(age=55, bmi=28.0, hba1c_last=7.5, baseline_glucose=8.0)
    result = classifier.predict(f)
    assert result.risk_level in RISK_LABELS


def test_predict_confidence_in_range(classifier: RiskClassifier) -> None:
    f = RiskFeatures(age=55, bmi=28.0, hba1c_last=7.5, baseline_glucose=8.0)
    result = classifier.predict(f)
    assert 0.0 <= result.confidence <= 1.0


def test_predict_top_features_non_empty(classifier: RiskClassifier) -> None:
    f = RiskFeatures(age=55, bmi=28.0, hba1c_last=7.5, baseline_glucose=8.0)
    result = classifier.predict(f)
    assert len(result.top_features) > 0


# ── clinical sanity checks ────────────────────────────────────────────────────

def test_high_risk_patient(classifier: RiskClassifier) -> None:
    """Very elevated HbA1c + glucose + comorbidities → high risk."""
    f = RiskFeatures(
        age=72,
        bmi=38.0,
        hba1c_last=11.5,
        baseline_glucose=13.0,
        current_glucose=15.0,
        symptom_count=5,
        has_hypertension=True,
        has_heart_disease=True,
        medication_count=4,
    )
    result = classifier.predict(f)
    assert result.risk_level == "high"


def test_current_glucose_used_when_provided(classifier: RiskClassifier) -> None:
    """When current_glucose differs from baseline, the model uses current_glucose."""
    base = RiskFeatures(age=50, bmi=27.0, hba1c_last=7.0, baseline_glucose=6.0)
    elevated = RiskFeatures(
        age=50, bmi=27.0, hba1c_last=7.0, baseline_glucose=6.0, current_glucose=14.0
    )
    r_base = classifier.predict(base)
    r_elevated = classifier.predict(elevated)
    # Elevated current glucose should push risk up
    risk_order = {k: i for i, k in enumerate(RISK_LABELS)}
    assert risk_order[r_elevated.risk_level] >= risk_order[r_base.risk_level]


def test_no_none_in_top_features(classifier: RiskClassifier) -> None:
    f = RiskFeatures(age=60, bmi=30.0, hba1c_last=8.0, baseline_glucose=9.0)
    result = classifier.predict(f)
    assert all(isinstance(feat, str) for feat in result.top_features)
