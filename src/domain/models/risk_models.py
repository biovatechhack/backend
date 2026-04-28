from __future__ import annotations

from pydantic import BaseModel, Field


class RiskFeatures(BaseModel):
    # ── Patient profile ───────────────────────────────────────────────────────
    age: int
    gender: str          # "M" | "F"
    bmi: float

    # ── Chronic context (derived from Patient record) ─────────────────────────
    hba1c: float
    has_hypertension: bool = False
    has_heart_disease: bool = False
    medication_count: int = 0

    # ── Real-time sensor vitals (mg/dL, bpm, %, steps, hours) ────────────────
    glucose: float
    hr: int
    spo2: int
    steps: int
    sleep_hours: float

    # ── Gemini-extracted symptom flags ────────────────────────────────────────
    confusion: bool = False
    tremors: bool = False
    thirst: bool = False


class RiskPrediction(BaseModel):
    risk_level: str  # "low" | "moderate" | "high"
    confidence: float = Field(ge=0.0, le=1.0)
    top_features: list[str] = Field(default_factory=list)
    # Per-class probability from EBM softmax
    class_probabilities: dict[str, float] = Field(default_factory=dict)
    # Additive EBM contribution of each feature toward the predicted class
    feature_contributions: dict[str, float] = Field(default_factory=dict)
