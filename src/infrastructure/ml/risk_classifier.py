from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from abstraction.ports.risk_port import RiskClassifierPort
from domain.models.risk_models import RiskFeatures, RiskPrediction

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).resolve().parents[4] / "models" / "risk_tree.pkl"

FEATURE_NAMES = [
    "age",
    "bmi",
    "hba1c_last",
    "baseline_glucose",
    "current_glucose",
    "symptom_count",
    "has_hypertension",
    "has_heart_disease",
    "medication_count",
]

RISK_LABELS = ["low", "medium", "high"]


class RiskClassifier(RiskClassifierPort):
    def __init__(self, model_path: Path = _MODEL_PATH) -> None:
        self._model: DecisionTreeClassifier = joblib.load(model_path)
        logger.info("Risk classifier loaded from %s", model_path)

    def predict(self, features: RiskFeatures) -> RiskPrediction:
        glucose = (
            features.current_glucose
            if features.current_glucose is not None
            else features.baseline_glucose
        )
        X = np.array(
            [[
                features.age,
                features.bmi,
                features.hba1c_last,
                features.baseline_glucose,
                glucose,
                features.symptom_count,
                int(features.has_hypertension),
                int(features.has_heart_disease),
                features.medication_count,
            ]]
        )

        label_idx = int(self._model.predict(X)[0])
        probas = self._model.predict_proba(X)[0]
        confidence = float(probas[label_idx])

        importances = self._model.feature_importances_
        top_indices = np.argsort(importances)[::-1][:3]
        top_features = [FEATURE_NAMES[i] for i in top_indices if importances[i] > 0]

        return RiskPrediction(
            risk_level=RISK_LABELS[label_idx],
            confidence=confidence,
            top_features=top_features,
        )
