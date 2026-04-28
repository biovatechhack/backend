from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
from interpret.glassbox import ExplainableBoostingClassifier

from abstraction.ports.risk_port import RiskClassifierPort
from domain.models.risk_models import RiskFeatures, RiskPrediction

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "risk_ebm.pkl"

# Order must match the training script's FEATURE_NAMES exactly
FEATURE_NAMES = [
    "age",
    "gender",           # encoded: 0 = M, 1 = F
    "bmi",
    "hba1c",
    "has_hypertension",
    "has_heart_disease",
    "medication_count",
    "glucose",
    "hr",
    "spo2",
    "steps",
    "sleep_hours",
    "confusion",
    "tremors",
    "thirst",
]

RISK_LABELS = ["low", "moderate", "high"]


class RiskClassifier(RiskClassifierPort):
    def __init__(self, model_path: Path = _MODEL_PATH) -> None:
        self._model: ExplainableBoostingClassifier = joblib.load(model_path)
        logger.info("EBM risk classifier loaded from %s", model_path)

    def predict(self, features: RiskFeatures) -> RiskPrediction:
        X = np.array([[
            features.age,
            1 if features.gender == "F" else 0,
            features.bmi,
            features.hba1c,
            int(features.has_hypertension),
            int(features.has_heart_disease),
            features.medication_count,
            features.glucose,
            features.hr,
            features.spo2,
            features.steps,
            features.sleep_hours,
            int(features.confusion),
            int(features.tremors),
            int(features.thirst),
        ]], dtype=float)

        label_idx = int(self._model.predict(X)[0])
        probas = self._model.predict_proba(X)[0]
        confidence = float(probas[label_idx])
        class_probabilities = {
            label: float(p) for label, p in zip(RISK_LABELS, probas, strict=True)
        }

        contributions = self._local_contributions(X, label_idx)
        top_features = sorted(
            contributions, key=lambda k: abs(contributions[k]), reverse=True
        )[:3]

        return RiskPrediction(
            risk_level=RISK_LABELS[label_idx],
            confidence=confidence,
            top_features=top_features,
            class_probabilities=class_probabilities,
            feature_contributions=contributions,
        )

    def _local_contributions(
        self, X: np.ndarray, label_idx: int
    ) -> dict[str, float]:
        try:
            explanation = self._model.explain_local(X)
            local_data = explanation.data(0)
            names: list[str] = local_data.get("names", FEATURE_NAMES)
            scores = np.array(local_data.get("scores", [0.0] * len(names)))

            # Multiclass EBM returns (n_terms, n_classes) — pick the predicted class
            if scores.ndim == 2:
                scores = (
                    scores[:, label_idx]
                    if scores.shape[0] == len(names)
                    else scores[label_idx]
                )

            return {
                n: float(s)
                for n, s in zip(names, scores, strict=False)
                if n != "Intercept"
            }
        except Exception:
            # Fallback: global term importances (not per-instance but always available)
            importances = self._model.term_importances()
            return dict(zip(FEATURE_NAMES, map(float, importances), strict=False))
