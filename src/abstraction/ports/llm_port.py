from abc import ABC, abstractmethod
from typing import Dict, Any, List

class LLMProvider(ABC):
    """Port for any LLM (DeepSeek or Gemini)"""

    @abstractmethod
    async def extract_clinical_entities(
        self, 
        darija_text: str, 
        glossary: dict
    ) -> Dict[str, Any]:
        """Call 1: Clinical entity extraction (structured JSON)"""
        pass

    @abstractmethod
    async def generate_response(
        self,
        risk_level: str,
        symptoms: List[str],
        patient_context: dict
    ) -> str:
        """Call 2: Culturally-appropriate Darija response"""
        pass