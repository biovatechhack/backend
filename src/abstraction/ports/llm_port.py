from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.llm_models import EntityExtractionResult


class LlmPort(ABC):
    @abstractmethod
    async def extract_entities(self, conversation_text: str) -> EntityExtractionResult:
        """Extract medical entities from a conversation turn."""

    @abstractmethod
    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        """Generate a clinically-aware response."""
