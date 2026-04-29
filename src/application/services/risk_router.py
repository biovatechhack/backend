from typing import Dict, Any
import uuid
from datetime import datetime

from domain.entities.risk_event import RiskEvent


class RiskRouter:
    """
    Sprint 2 - Dev A responsibility
    Pure business logic: decides what to do based on risk score
    """

    @staticmethod
    def decide(
        risk_score: Dict[str, Any],
        patient_id: str,
        conversation_log_id: str
    ) -> Dict[str, Any]:
        risk = risk_score["risk"]

        # Create RiskEvent entity (as per your domain)
        event = RiskEvent(
            id=str(uuid.uuid4()),
            patient_id=patient_id,
            conversation_log_id=conversation_log_id,
            risk_level=risk,
            confidence=risk_score["confidence"],
            timestamp=datetime.utcnow(),
            extracted_symptoms=[],  # will be filled by UseCase if needed
            top_decision_features=risk_score.get("top_features", []),
            biometric_passed=False,
            alerts_sent=[]
        )

        if risk == "HIGH":
            return {
                "action": "alert",
                "risk_event": event,
                "requires_biometric": True,
                "nurse_guardrail": "راسلو طبيبك قبل ما تبدل أي دواء أو جرعة"
            }
        elif risk == "MODERATE":
            return {
                "action": "advice",
                "risk_event": event,
                "requires_biometric": False
            }
        else:  # LOW
            return {
                "action": "log_only",
                "risk_event": event,
                "requires_biometric": False
            }