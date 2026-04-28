from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class EntityExtractionResult(BaseModel):
    """Result of LLM Call 1 (matches your LlmPort)"""
    symptoms: List[str] = Field(default_factory=list)
    severity_hints: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    darija_confidence: float = 0.0
    raw_json: Optional[Dict[str, Any]] = None   # for debugging