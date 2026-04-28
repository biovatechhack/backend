from typing import Dict, Any
from infrastructure.sensors.bracelet_simulator import BraceletSimulator

class FeatureMapper:
    """
    TEMPORARY SIMULATION — Dev B will replace this later with the real complex version.
    This version is enough for you to test the full flow now.
    """

    @staticmethod
    def build_feature_vector_from_session(
        patient_id: str,
        extraction: Dict[str, Any],
        bracelet: Any,                    # BraceletReading object
        previous_turns: list = None
    ) -> Dict[str, Any]:
        
        symptoms = extraction.get("symptoms", [])
        
        return {
            # Profile (static for demo)
            "age": 62,
            "gender": 0,                    # 0 = Male
            "bmi": 28.4,
            "hba1c": 8.1,
            "has_hypertension": 1,
            "has_heart_disease": 0,
            "medication_count": 2,

            # Real-time bracelet data (sensor)
            "glucose": bracelet.glucose_mg_dl,
            "hr": bracelet.heart_rate_bpm,
            "spo2": bracelet.spo2_pct,
            "steps": bracelet.steps_today,
            "sleep_hours": bracelet.sleep_hours,

            # Symptoms from all turns (Gemini extraction)
            "confusion": int(any("دوخ" in s or "دوار" in s or "confusion" in s.lower() for s in symptoms)),
            "tremors": int(any("ترتعش" in s or "tremors" in s.lower() for s in symptoms)),
            "thirst": int(any("عطاش" in s or "thirst" in s.lower() for s in symptoms)),
            
            # Overall severity
            "symptom_severity": len(symptoms) * 1.3,
        }