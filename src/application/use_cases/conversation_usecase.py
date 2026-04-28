from typing import Dict, Any
import uuid
from datetime import datetime
from dataclasses import asdict

from domain.entities.conversation_turn import ConversationTurn
from domain.models.api_schemas import ConversationRequest, ConversationResponse, ClinicalExtraction, RiskScore
from domain.models.llm_models import EntityExtractionResult
from abstraction.ports.llm_port import LlmPort
from abstraction.ports.ml_port import RiskScorer
from infrastructure.cache.redis_session import RedisSessionCache
from infrastructure.sensors.bracelet_simulator import BraceletSimulator
from application.services.feature_mapper import FeatureMapper
from application.services.risk_router import RiskRouter
from infrastructure.intelligence.glossary import load_glossary


class ConversationUseCase:
    def __init__(self, llm: LlmPort, risk_scorer: RiskScorer):
        self.llm = llm
        self.risk_scorer = risk_scorer

    async def execute(self, request: ConversationRequest, session_id: str | None = None) -> ConversationResponse:
        session_id = session_id or str(uuid.uuid4())
        patient_id = request.patient_id

        # Load session (this gives us memory)
        session = await RedisSessionCache.get_session(session_id) or {
            "turns": [],
            "accumulated_symptoms": []
        }

        bracelet = BraceletSimulator.get_current_reading(patient_id)

        # LLM Call 1 - Extract symptoms
        extraction_result: EntityExtractionResult = await self.llm.extract_entities(request.message_darija)
        session["accumulated_symptoms"].extend(extraction_result.symptoms)

        # Build full history for LLM memory
        history = "\n".join([t["content_darija"] for t in session["turns"]])

        # ==================== INVESTIGATOR MODE (keep asking questions) ====================
        if extraction_result.darija_confidence < 0.85 and len(extraction_result.missing_fields) > 0 and len(session["turns"]) < 8:
            follow_up = await self.llm.generate_response(
                system_prompt="You are Nour, a caring Algerian nurse. Ask ONE short, natural follow-up question in Darija to better understand the patient's symptoms. Do not give advice yet.",
                user_message=f"Previous messages:\n{history}\nCurrent message: {request.message_darija}\nMissing info: {extraction_result.missing_fields}"
            )

            return ConversationResponse(
                session_id=session_id,
                nurse_message_darija=follow_up,
                risk_level="PENDING",
                requires_biometric=False,
                conversation_log_id=None,
                extracted=ClinicalExtraction(**extraction_result.dict())   # ← always fill extracted
            )

        # ==================== END OF INTERVIEW → Trigger Dev2 work ====================
        features = FeatureMapper.build_feature_vector_from_session(
            patient_id=patient_id,
            extraction=extraction_result.dict(),
            bracelet=bracelet,
            previous_turns=session["turns"]
        )

        risk_score_dict = await self.risk_scorer.score(features)
        risk_score = RiskScore(**risk_score_dict)

        log_id = str(uuid.uuid4())
        decision = RiskRouter.decide(risk_score_dict, patient_id, log_id)

        nurse_message = await self.llm.generate_response(
            system_prompt="You are Nour, a warm Algerian digital nurse. Give a clear, caring final response in natural Darija.",
            user_message=f"Previous conversation:\n{history}\nLast message: {request.message_darija}\nRisk: {risk_score.risk}"
        )

        # Save turn
        turn = ConversationTurn(
            id=str(uuid.uuid4()),
            conversation_log_id=log_id,
            role="patient",
            content_darija=request.message_darija,
            turn_timestamp=datetime.utcnow(),
            risk_at_turn=risk_score.risk
        )
        session["turns"].append(asdict(turn))
        await RedisSessionCache.set_session(session_id, session)

        return ConversationResponse(
            session_id=session_id,
            nurse_message_darija=nurse_message,
            risk_level=risk_score.risk,
            requires_biometric=decision.get("requires_biometric", False),
            conversation_log_id=log_id,
            extracted=ClinicalExtraction(**extraction_result.dict())
        )