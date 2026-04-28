from __future__ import annotations

from pydantic import BaseModel, Field


class EntityExtractionResult(BaseModel):
    medications: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    vital_signs: dict[str, str] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
