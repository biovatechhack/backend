import joblib
from pathlib import Path
from typing import Dict, Any
from abstraction.ports.ml_port import RiskScorer
from interpret.glassbox import ExplainableBoostingClassifier

class RealRiskScorer(RiskScorer):
    _model: ExplainableBoostingClassifier | None = None
    # Fix: Use path relative to this file to find the models directory in the project root
    MODEL_PATH = Path(__file__).parent.parent.parent.parent / "models" / "risk_ebm.pkl"

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            if not cls.MODEL_PATH.exists():
                raise FileNotFoundError(f"Model not found at {cls.MODEL_PATH}. Run training first.")
            cls._model = joblib.load(cls.MODEL_PATH)
        return cls._model

    async def score(self, features: Dict[str, Any]) -> Dict[str, Any]:
        model = self._load_model()
        
        # Map your feature dict to the exact order used in training
        feature_vector = [
            features.get("age", 60),
            features.get("gender", 0),           # 0=M, 1=F
            features.get("bmi", 28.0),
            features.get("hba1c", 7.5),
            features.get("has_hypertension", 1),
            features.get("has_heart_disease", 0),
            features.get("medication_count", 2),
            features.get("glucose", 120.0),
            features.get("hr", 80),
            features.get("spo2", 97),
            features.get("steps", 5000),
            features.get("sleep_hours", 7.0),
            features.get("confusion", 0),
            features.get("tremors", 0),
            features.get("thirst", 0),
        ]

        pred = model.predict([feature_vector])[0]
        proba = model.predict_proba([feature_vector])[0]

        risk_map = {0: "LOW", 1: "MODERATE", 2: "HIGH"}
        risk = risk_map[pred]

        return {
            "risk": risk,
            "confidence": float(max(proba)),
            "top_features": ["glucose", "symptom_severity", "hr"]   # can be improved later
        }