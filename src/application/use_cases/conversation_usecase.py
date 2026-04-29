"""
ConversationUseCase — Phase 1: Structured Clinical Symptom Interview

The LLM plays the role of a medical interviewer (Nour, an Algerian digital
health assistant).  It does NOT diagnose — it systematically collects symptoms
across 7 clinical dimensions in at most 7 questions, then produces a warm
non-diagnostic recommendation and signals the end of the conversation.

At interview close:
  • Sensor data is fetched from the bracelet simulator
  • The feature vector is built (symptoms + vitals + patient metadata)
  • The ML model scores the risk level
  • The result is returned with interview_complete=True, ready for Phase 2

Session state schema (stored in Redis):
  {
    "turns":                 [{"role", "content_darija", "turn_timestamp"}, ...],
    "accumulated_symptoms":  ["symptom1", ...],           -- deduplicated list
    "covered_dimensions":    ["chief_complaint", ...],    -- confirmed so far
    "question_count":        int,                          -- nurse questions asked
    "is_complete":           bool
  }
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from abstraction.ports.llm_port import LlmPort
from abstraction.ports.ml_port import RiskScorer
from abstraction.ports.notification_port import NotificationPort
from abstraction.repositories.patient_repository_port import PatientRepositoryPort
from application.services.feature_mapper import FeatureMapper
from application.services.risk_router import RiskRouter
from domain.models.api_schemas import (
    ClinicalExtraction,
    ConversationRequest,
    ConversationResponse,
    RiskScore,
)
from domain.models.llm_models import EntityExtractionResult
from domain.models.risk_models import RiskPrediction
from infrastructure.cache.redis_session import RedisSessionCache
from infrastructure.intelligence.patient_profile_loader import PatientProfileLoader
from infrastructure.sensors.bracelet_simulator import BraceletSimulator

logger = logging.getLogger(__name__)


# ── Clinical dimensions the interviewer must cover, in priority order ─────────
CLINICAL_DIMENSIONS: List[str] = [
    "chief_complaint",      # What is the main problem?
    "onset",                # When did symptoms start?
    "duration",             # How long has this been going on?
    "severity",             # How severe? (mild / moderate / severe)
    "associated_symptoms",  # Any other symptoms alongside the main one?
    "aggravating_factors",  # What makes it worse?
    "context",              # Recent meals, medication taken, activity level?
]

# Friendly question hints passed to the LLM for each dimension
_DIMENSION_HINTS: Dict[str, str] = {
    "chief_complaint":     "Ask what is mainly bothering them today.",
    "onset":               "Ask when these symptoms first appeared.",
    "duration":            "Ask how long they've been feeling this way.",
    "severity":            "Ask how severe the symptoms are (use simple descriptors like خفيف / متوسط / شديد).",
    "associated_symptoms": "Ask if they feel anything else alongside the main symptom.",
    "aggravating_factors": "Ask what makes the symptoms worse (movement, eating, stress…).",
    "context":             "Ask about recent meals, whether they took their medication today, and their activity level.",
}

# Early-stop thresholds (close before reaching 7 questions if we have enough)
_EARLY_STOP_MIN_SYMPTOMS = 4
_EARLY_STOP_REQUIRED_DIMS = {"chief_complaint", "onset", "duration", "severity"}


class ConversationUseCase:
    """
    Orchestrates the patient-facing symptom interview.

    Phase 1 (this file): structured LLM interview → recommendation → end.
    Phase 2 (next sprint): sensor data + patient metadata → ML classification → routing.
    """

    MAX_QUESTIONS = 7  # hard cap on nurse questions

    def __init__(
        self,
        llm: LlmPort,
        risk_scorer: RiskScorer,
        notifications: list[NotificationPort] | None = None,
        patient_repo: PatientRepositoryPort | None = None,
    ) -> None:
        self.llm = llm
        self.risk_scorer = risk_scorer
        self._notifications: list[NotificationPort] = notifications or []
        self._patient_repo = patient_repo

    # ── Public entry point ───────────────────────────────────────────────────

    async def execute(
        self,
        request: ConversationRequest,
        session_id: Optional[str] = None,
    ) -> ConversationResponse:
        """
        Process one patient turn and return the nurse's next move.

        Args:
            request:    patient_id + message_darija
            session_id: Redis key (None → new session)

        Returns:
            ConversationResponse with interview_complete=False while collecting
            symptoms, True once the interview ends and the ML pipeline runs.
        """
        session_id = session_id or str(uuid.uuid4())
        patient_id = request.patient_id

        # ── 1. Load or initialise session ──────────────────────────────────
        session: Dict[str, Any] = (
            await RedisSessionCache.get_session(session_id)
            or self._init_session()
        )

        # Guard: already completed (e.g., duplicate call)
        if session.get("is_complete", False):
            return ConversationResponse(
                session_id=session_id,
                nurse_message_darija="شكراً. المقابلة انتهت من قبل. الطبيب راجع ملفك.",
                risk_level=session.get("final_risk_level", "PENDING"),
                interview_complete=True,
                requires_biometric=False,
                conversation_log_id=session.get("conversation_log_id"),
                question_count=session["question_count"],
                extracted=None,
            )

        # ── 2. Append patient turn ──────────────────────────────────────────
        session["turns"].append({
            "role": "patient",
            "content_darija": request.message_darija,
            "turn_timestamp": datetime.utcnow().isoformat(),
        })

        # ── 3. Extract symptoms & clinical entities from this turn ──────────
        extraction: EntityExtractionResult = await self.llm.extract_entities(
            request.message_darija
        )

        # Accumulate unique symptoms across turns
        for symptom in extraction.symptoms:
            if symptom and symptom not in session["accumulated_symptoms"]:
                session["accumulated_symptoms"].append(symptom)

        # Mark which clinical dimensions are now confirmed
        self._update_dimension_coverage(session, extraction)

        history_text = self._build_history(session["turns"])

        # ── 4. Decide: continue interview OR close ──────────────────────────
        if not self._should_close_interview(session):
            # ── 4a. Ask the next targeted clinical question ─────────────────
            nurse_question = await self._ask_next_question(
                session=session,
                history_text=history_text,
                extraction=extraction,
            )
            session["question_count"] += 1
            session["turns"].append({
                "role": "nurse",
                "content_darija": nurse_question,
                "turn_timestamp": datetime.utcnow().isoformat(),
            })
            await RedisSessionCache.set_session(session_id, session)

            return ConversationResponse(
                session_id=session_id,
                nurse_message_darija=nurse_question,
                risk_level="PENDING",
                interview_complete=False,
                requires_biometric=False,
                conversation_log_id=None,
                question_count=session["question_count"],
                extracted=ClinicalExtraction(**extraction.dict()),
            )

        # ── 5. Interview complete — run the ML pipeline ─────────────────────

        # 5a. Fetch real patient profile from Supabase
        #     → 7 static features: age, gender, bmi, hba1c,
        #       has_hypertension, has_heart_disease, medication_count
        patient_profile = await PatientProfileLoader.load(patient_id)

        # 5b. Fetch real-time sensor data from bracelet simulator
        #     → 5 features: glucose, hr, spo2, steps, sleep_hours
        bracelet = BraceletSimulator.get_current_reading(patient_id)

        # 5c. Build the complete 15-feature vector for the EBM model
        #     IMPORTANT: use session["accumulated_symptoms"] (all turns),
        #     NOT extraction.dict()["symptoms"] (last turn only)
        features = FeatureMapper.build(
            patient_profile=patient_profile,
            bracelet=bracelet,
            accumulated_symptoms=session["accumulated_symptoms"],
        )

        # 5d. ML risk scoring
        risk_score_dict = await self.risk_scorer.score(features)
        risk_score = RiskScore(**risk_score_dict)

        # 5d. Risk routing decision (HIGH → biometric required, etc.)
        log_id = str(uuid.uuid4())
        decision = RiskRouter.decide(risk_score_dict, patient_id, log_id)

        # 5e. Fire alert notifications for HIGH risk
        if risk_score.risk == "HIGH" and self._notifications and self._patient_repo:
            patient_entity = await self._patient_repo.get_by_id(patient_id)
            if patient_entity:
                prediction = RiskPrediction(
                    risk_level=risk_score.risk.lower(),
                    confidence=risk_score.confidence,
                    top_features=risk_score.top_features,
                )
                for adapter in self._notifications:
                    try:
                        sent = await adapter.send(patient=patient_entity, prediction=prediction)
                        if sent:
                            logger.info(
                                "notification sent channel=%s patient=%s",
                                adapter.channel_name, patient_id,
                            )
                        else:
                            logger.warning(
                                "notification skipped channel=%s patient=%s",
                                adapter.channel_name, patient_id,
                            )
                    except Exception as exc:
                        logger.error(
                            "notification error channel=%s patient=%s: %s",
                            adapter.channel_name, patient_id, exc,
                        )

        # 5g. Generate warm, safe closing recommendation (NOT a diagnosis)
        final_message = await self._generate_final_recommendation(
            session=session,
            history_text=history_text,
            risk_level=risk_score.risk,
        )

        session["turns"].append({
            "role": "nurse",
            "content_darija": final_message,
            "turn_timestamp": datetime.utcnow().isoformat(),
        })
        session["is_complete"] = True
        session["final_risk_level"] = risk_score.risk
        session["conversation_log_id"] = log_id
        await RedisSessionCache.set_session(session_id, session)

        return ConversationResponse(
            session_id=session_id,
            nurse_message_darija=final_message,
            risk_level=risk_score.risk,
            interview_complete=True,
            requires_biometric=decision.get("requires_biometric", False),
            conversation_log_id=log_id,
            question_count=session["question_count"],
            extracted=ClinicalExtraction(**extraction.dict()),
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _init_session() -> Dict[str, Any]:
        """Return a clean, empty session state."""
        return {
            "turns": [],
            "accumulated_symptoms": [],
            "covered_dimensions": [],   # List[str] from CLINICAL_DIMENSIONS
            "question_count": 0,        # how many nurse questions asked so far
            "is_complete": False,
            "final_risk_level": "PENDING",
            "conversation_log_id": None,
        }

    @staticmethod
    def _build_history(turns: List[Dict]) -> str:
        """Format all turns as a readable conversation string."""
        return "\n".join(
            f"{t['role'].upper()}: {t['content_darija']}"
            for t in turns
        )

    @staticmethod
    def _update_dimension_coverage(
        session: Dict[str, Any],
        extraction: EntityExtractionResult,
    ) -> None:
        """
        A dimension is considered 'covered' if it is NOT present in
        the extraction's missing_fields list.

        The DeepSeek extraction prompt returns missing_fields using the
        exact CLINICAL_DIMENSIONS names, so set subtraction is reliable.
        """
        all_dims = set(CLINICAL_DIMENSIONS)
        still_missing = set(extraction.missing_fields)
        newly_covered = all_dims - still_missing

        covered = set(session.get("covered_dimensions", []))
        covered.update(newly_covered)
        session["covered_dimensions"] = list(covered)

    def _should_close_interview(self, session: Dict[str, Any]) -> bool:
        """
        Return True (close interview) when either:
          • Hard cap: 7 questions have been asked, OR
          • Early stop: ≥ 4 symptoms collected AND the 4 key clinical
            dimensions (chief_complaint, onset, duration, severity)
            are all confirmed.
        """
        if session["question_count"] >= self.MAX_QUESTIONS:
            return True

        symptom_count = len(session["accumulated_symptoms"])
        covered = set(session.get("covered_dimensions", []))
        early_stop = (
            symptom_count >= _EARLY_STOP_MIN_SYMPTOMS
            and _EARLY_STOP_REQUIRED_DIMS.issubset(covered)
        )
        return early_stop

    async def _ask_next_question(
        self,
        session: Dict[str, Any],
        history_text: str,
        extraction: EntityExtractionResult,
    ) -> str:
        """
        Generate ONE focused follow-up question in Algerian Darija targeting
        the highest-priority uncovered clinical dimension.
        """
        covered = set(session.get("covered_dimensions", []))
        uncovered = [d for d in CLINICAL_DIMENSIONS if d not in covered]
        target_dim = uncovered[0] if uncovered else "associated_symptoms"

        q_num = session["question_count"] + 1   # 1-indexed for the prompt
        symptoms_so_far = session["accumulated_symptoms"]

        system_prompt = (
            "You are Nour, a warm and empathetic Algerian digital health assistant "
            "specialised in supporting diabetic patients. "
            "You speak fluent Algerian Darija, naturally mixing in French words the way "
            "Algerians do in everyday speech (e.g. 'واش تحس بـ fatigue?'). "
            "Your sole mission right now is to collect enough clinical information "
            "so the doctor can assess the patient properly — you do NOT diagnose. "
            "\n\nRULES:"
            "\n• Ask EXACTLY ONE short, natural, conversational question — nothing more."
            "\n• Do NOT number the question."
            "\n• Do NOT add preamble, explanation, or advice."
            "\n• Do NOT repeat any information the patient already gave."
            f"\n• This is question {q_num} of {self.MAX_QUESTIONS} — keep it concise."
        )

        user_message = (
            f"Conversation so far:\n{history_text}\n\n"
            f"Symptoms identified so far: {symptoms_so_far}\n"
            f"Most important missing clinical information: '{target_dim}'\n"
            f"Hint for this dimension: {_DIMENSION_HINTS.get(target_dim, '')}\n\n"
            "Generate the next single question in Algerian Darija "
            "(mix in French naturally where appropriate)."
        )

        return await self.llm.generate_response(
            system_prompt=system_prompt,
            user_message=user_message,
        )

    async def _generate_final_recommendation(
        self,
        session: Dict[str, Any],
        history_text: str,
        risk_level: str,
    ) -> str:
        """
        Generate a warm, safe, non-diagnostic closing message.

        Structure:
          1. Empathetic acknowledgement
          2. 2–3 practical, safe self-care tips
          3. Reassurance that the doctor will review their case
          4. Natural conversation closer
        """
        symptoms = session["accumulated_symptoms"]
        q_count = session["question_count"]

        system_prompt = (
            "You are Nour, a warm and caring Algerian digital health assistant. "
            "You speak Algerian Darija naturally mixed with French. "
            "The symptom interview is now COMPLETE. Write a closing message that includes:\n"
            "1. A brief empathetic acknowledgement of what the patient shared "
            "(2 sentences max, do not list symptoms back at them).\n"
            "2. Two or three simple, safe, practical self-care tips relevant "
            "to their symptoms (e.g., rest, hydrate, check glucose, avoid exertion). "
            "These are general wellness tips — NOT medical prescriptions or doses.\n"
            "3. Tell them clearly that their information has been noted and their "
            "doctor will review their case shortly.\n"
            "4. A natural, warm goodbye that signals the conversation is over.\n\n"
            "STRICT RULES:\n"
            "• NEVER say 'you have [disease]' — this is NOT a diagnosis.\n"
            "• NEVER recommend specific prescription drugs or specific doses.\n"
            "• If risk level is HIGH, add an urgent but calm note to seek "
            "medical attention quickly or call their doctor.\n"
            "• Keep the entire message to 4–6 sentences.\n"
            "• Tone: warm, reassuring, professional."
        )

        urgency_note = ""
        if risk_level == "HIGH":
            urgency_note = (
                "\n⚠️  Internal risk model flagged this as HIGH risk. "
                "Add a calm but clear note for the patient to contact their doctor urgently "
                "or go to the nearest clinic today."
            )
        elif risk_level == "MODERATE":
            urgency_note = (
                "\nℹ️  Internal risk model: MODERATE. "
                "Encourage them to rest and monitor, and to call if symptoms worsen."
            )

        user_message = (
            f"Full conversation:\n{history_text}\n\n"
            f"All symptoms collected ({len(symptoms)} total): {symptoms}\n"
            f"Number of questions asked: {q_count} / {self.MAX_QUESTIONS}\n"
            f"Internal risk level (do not reveal to patient): {risk_level}"
            f"{urgency_note}\n\n"
            "Write the closing recommendation message in Algerian Darija."
        )

        return await self.llm.generate_response(
            system_prompt=system_prompt,
            user_message=user_message,
        )