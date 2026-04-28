from __future__ import annotations

from pydantic import BaseModel, Field


class RiskFeatures(BaseModel):
    age: int
    bmi: float
    hba1c_last: float
    baseline_glucose: float
    current_glucose: float | None = None
    symptom_count: int = 0
    has_hypertension: bool = False
    has_heart_disease: bool = False
    medication_count: int = 0


class RiskPrediction(BaseModel):
    risk_level: str  # "low" | "medium" | "high"
    confidence: float = Field(ge=0.0, le=1.0)
    top_features: list[str] = Field(default_factory=list)
