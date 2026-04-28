from pydantic import BaseModel, Field
from typing import List, Optional

class ClinicalExtraction(BaseModel):
    symptoms: List[str] = Field(default_factory=list)
    severity_hints: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    darija_confidence: float = 0.0

class RiskScore(BaseModel):
    risk: str
    confidence: float
    top_features: List[str] = Field(default_factory=list)

class ConversationRequest(BaseModel):
    patient_id: str
    message_darija: str

class ConversationResponse(BaseModel):
    session_id: str
    nurse_message_darija: str
    risk_level: str = "PENDING"               # stays PENDING during questioning
    interview_complete: bool = False          # ← NEW: this tells you when interrogation ends
    requires_biometric: bool = False
    conversation_log_id: Optional[str] = None
    extracted: Optional[ClinicalExtraction] = None