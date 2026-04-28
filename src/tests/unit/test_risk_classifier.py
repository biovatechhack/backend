from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.models.risk_models import RiskFeatures, RiskPrediction
from src.infrastructure.ml.risk_classifier import RISK_LABELS, RiskClassifier

MODEL_PATH = Path(__file__).resolve().parents[4] / "models" / "risk_ebm.pkl"

_BASE = RiskFeatures(
    age=55,
    hba1c=7.5,
    glucose=140.0,
    hr=78,
    spo2=97,
    steps=5000,
    sleep_hours=7.0,
)


@pytest.fixture(scope="module")
def classifier() -> RiskClassifier:
    return RiskClassifier(model_path=MODEL_PATH)


# ── basic contract ────────────────────────────────────────────────────────────

def test_model_file_exists() -> None:
    assert MODEL_PATH.exists(), "models/risk_ebm.pkl missing — run src/scripts/train_risk_ebm.py"


def test_classifier_loads(classifier: RiskClassifier) -> None:
    assert classifier is not None


def test_predict_returns_risk_prediction(classifier: RiskClassifier) -> None:
    assert isinstance(classifier.predict(_BASE), RiskPrediction)


def test_predict_risk_level_is_valid(classifier: RiskClassifier) -> None:
    assert classifier.predict(_BASE).risk_level in RISK_LABELS


def test_predict_confidence_in_range(classifier: RiskClassifier) -> None:
    result = classifier.predict(_BASE)
    assert 0.0 <= result.confidence <= 1.0


def test_predict_top_features_non_empty(classifier: RiskClassifier) -> None:
    assert len(classifier.predict(_BASE).top_features) > 0


def test_predict_class_probabilities_sum_to_one(classifier: RiskClassifier) -> None:
    probs = classifier.predict(_BASE).class_probabilities
    assert set(probs.keys()) == set(RISK_LABELS)
    assert abs(sum(probs.values()) - 1.0) < 1e-6


def test_predict_feature_contributions_present(classifier: RiskClassifier) -> None:
    contribs = classifier.predict(_BASE).feature_contributions
    assert len(contribs) > 0
    assert all(isinstance(v, float) for v in contribs.values())


def test_no_none_in_top_features(classifier: RiskClassifier) -> None:
    assert all(isinstance(f, str) for f in classifier.predict(_BASE).top_features)


# ── clinical sanity checks ────────────────────────────────────────────────────

def test_high_risk_hyperglycaemia(classifier: RiskClassifier) -> None:
    """Severe hyperglycaemia with confusion → high risk."""
    f = RiskFeatures(
        age=70,
        hba1c=11.5,
        glucose=380.0,
        hr=100,
        spo2=91,
        steps=800,
        sleep_hours=5.0,
        confusion=True,
        thirst=True,
    )
    assert classifier.predict(f).risk_level == "high"


def test_high_risk_hypoglycaemia(classifier: RiskClassifier) -> None:
    """Severe hypoglycaemia with tremors and tachycardia → high risk."""
    f = RiskFeatures(
        age=60,
        hba1c=7.0,
        glucose=48.0,
        hr=120,
        spo2=92,
        steps=1000,
        sleep_hours=4.5,
        tremors=True,
        confusion=True,
    )
    assert classifier.predict(f).risk_level == "high"


def test_low_risk_patient(classifier: RiskClassifier) -> None:
    """Normal glucose, good vitals, no symptoms → low risk."""
    f = RiskFeatures(
        age=35,
        hba1c=5.5,
        glucose=105.0,
        hr=68,
        spo2=99,
        steps=10000,
        sleep_hours=8.0,
    )
    assert classifier.predict(f).risk_level == "low"


def test_elevated_glucose_raises_risk(classifier: RiskClassifier) -> None:
    """Higher glucose should not lower the predicted risk level."""
    low_glucose = RiskFeatures(
        age=50, hba1c=7.0, glucose=110.0, hr=75, spo2=98, steps=6000, sleep_hours=7.5
    )
    high_glucose = RiskFeatures(
        age=50, hba1c=7.0, glucose=320.0, hr=75, spo2=98, steps=6000, sleep_hours=7.5
    )
    risk_order = {k: i for i, k in enumerate(RISK_LABELS)}
    r_low = classifier.predict(low_glucose)
    r_high = classifier.predict(high_glucose)
    assert risk_order[r_high.risk_level] >= risk_order[r_low.risk_level]
