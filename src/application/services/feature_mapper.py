"""
FeatureMapper
=============
Builds the 15-dimensional feature vector required by the EBM risk classifier.

Feature groups (must exactly match the training script's FEATURE_NAMES):

  ┌────────────────────────────────────────┬────────────────────────────────┐
  │  Patient static profile  (7 features)  │  From Supabase `patients` row  │
  ├────────────────────────────────────────┼────────────────────────────────┤
  │  age                                   │  int                           │
  │  gender                                │  0=Male / 1=Female             │
  │  bmi                                   │  float                         │
  │  hba1c                                 │  float (HbA1c %)               │
  │  has_hypertension                      │  0 / 1                         │
  │  has_heart_disease                     │  0 / 1                         │
  │  medication_count                      │  int (len of medications list) │
  ├────────────────────────────────────────┼────────────────────────────────┤
  │  Sensor / bracelet  (5 features)       │  From BraceletSimulator        │
  ├────────────────────────────────────────┼────────────────────────────────┤
  │  glucose                               │  mg/dL float                   │
  │  hr                                    │  bpm int                       │
  │  spo2                                  │  % int                         │
  │  steps                                 │  int (today)                   │
  │  sleep_hours                           │  float                         │
  ├────────────────────────────────────────┼────────────────────────────────┤
  │  Symptom binary flags  (3 features)    │  From accumulated_symptoms     │
  ├────────────────────────────────────────┼────────────────────────────────┤
  │  confusion                             │  0 / 1                         │
  │  tremors                               │  0 / 1                         │
  │  thirst                                │  0 / 1                         │
  └────────────────────────────────────────┴────────────────────────────────┘
"""
from __future__ import annotations

from typing import Any, Dict, List


# ── Symptom keyword dictionaries (Darija + French + clinical English) ─────────

_CONFUSION_KW = {
    "دوخ", "دوار", "confusion", "confused", "دizziness", "dizziness",
    "vertigo", "vertige", "مش واعي", "غياب الوعي", "مايفهمش",
    "rأسي يدور",
}
_TREMOR_KW = {
    "ترتعش", "يرتعش", "رعشة", "tremors", "tremor", "shaking",
    "رجليا ترتعش", "tremblement", "يرجف",
}
_THIRST_KW = {
    "عطاش", "عطشان", "عطش", "نشاف", "thirst", "thirsty",
    "soif", "soif excessive", "عطشت",
}


def _symptom_flag(accumulated_symptoms: List[str], keywords: set) -> int:
    """
    Return 1 if any symptom string contains at least one keyword.
    Both symptom strings and keywords are lowercased for matching.
    """
    symptoms_lc = [s.lower() for s in accumulated_symptoms]
    for kw in keywords:
        kw_lc = kw.lower()
        if any(kw_lc in s for s in symptoms_lc):
            return 1
    return 0


class FeatureMapper:
    """
    Stateless utility that assembles the full 15-feature vector.

    Primary API::

        features = FeatureMapper.build(
            patient_profile    = await PatientProfileLoader.load(patient_id),
            bracelet           = BraceletSimulator.get_current_reading(patient_id),
            accumulated_symptoms = session["accumulated_symptoms"],
        )

    Legacy shim (backward-compatible, uses hardcoded defaults)::

        features = FeatureMapper.build_feature_vector_from_session(...)
    """

    # ── Primary method ────────────────────────────────────────────────────────

    @staticmethod
    def build(
        patient_profile: Dict[str, Any],
        bracelet: Any,                        # BraceletReading dataclass
        accumulated_symptoms: List[str],
    ) -> Dict[str, Any]:
        """
        Assemble all 15 features from the three data sources.

        Args:
            patient_profile:      dict from PatientProfileLoader.load()
            bracelet:             BraceletReading from BraceletSimulator
            accumulated_symptoms: full list of symptoms collected across all turns

        Returns:
            Flat dict keyed by EBM training feature names.
        """
        return {
            # ── Group 1: Patient static profile ──────────────────────────────
            "age":               patient_profile.get("age", 60),
            "gender":            patient_profile.get("gender", 0),
            "bmi":               patient_profile.get("bmi", 27.0),
            "hba1c":             patient_profile.get("hba1c", 7.5),
            "has_hypertension":  patient_profile.get("has_hypertension", 0),
            "has_heart_disease": patient_profile.get("has_heart_disease", 0),
            "medication_count":  patient_profile.get("medication_count", 1),

            # ── Group 2: Real-time bracelet sensor readings ───────────────────
            "glucose":           bracelet.glucose_mg_dl,
            "hr":                bracelet.heart_rate_bpm,
            "spo2":              bracelet.spo2_pct,
            "steps":             bracelet.steps_today,
            "sleep_hours":       bracelet.sleep_hours,

            # ── Group 3: Symptom binary flags (from entire conversation) ──────
            "confusion":         _symptom_flag(accumulated_symptoms, _CONFUSION_KW),
            "tremors":           _symptom_flag(accumulated_symptoms, _TREMOR_KW),
            "thirst":            _symptom_flag(accumulated_symptoms, _THIRST_KW),
        }

    # ── Legacy shim (keeps old test code working) ─────────────────────────────

    @staticmethod
    def build_feature_vector_from_session(
        patient_id: str,
        extraction: Dict[str, Any],
        bracelet: Any,
        previous_turns: list = None,
    ) -> Dict[str, Any]:
        """
        Backward-compatible wrapper.
        Prefer FeatureMapper.build() with PatientProfileLoader in new code.
        """
        symptoms = extraction.get("symptoms", [])
        _default_profile = {
            "age": 62, "gender": 0, "bmi": 28.4, "hba1c": 8.1,
            "has_hypertension": 1, "has_heart_disease": 0, "medication_count": 2,
        }
        return FeatureMapper.build(_default_profile, bracelet, symptoms)