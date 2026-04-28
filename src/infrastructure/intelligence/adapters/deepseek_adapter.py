from openai import AsyncOpenAI
import json
from typing import Dict, Any

from abstraction.ports.llm_port import LlmPort
from domain.models.llm_models import EntityExtractionResult
from infrastructure.config.settings import settings
from infrastructure.intelligence.glossary import load_glossary


class DeepSeekAdapter(LlmPort):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        self.model = "deepseek-chat"

    async def extract_entities(self, conversation_text: str) -> EntityExtractionResult:
        """LLM Call 1: Strict symptom extraction"""
        glossary = load_glossary()

        system_prompt = f"""You are a clinical NLP engine for Algerian Darija.
Return ONLY valid JSON. Never add explanation.

Use this glossary:
{json.dumps(glossary, ensure_ascii=False)}

Extract from patient message and return exactly:
{{"symptoms": ["list", "of", "symptoms"],
  "severity_hints": ["list", "of", "hints"],
  "missing_fields": ["list", "of", "missing", "info"],
  "darija_confidence": 0.0 to 1.0}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Patient: {conversation_text}"}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        data = json.loads(response.choices[0].message.content)
        return EntityExtractionResult(**data)

    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        """LLM Call 2: Natural Darija response or follow-up question"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=180
        )
        return response.choices[0].message.content.strip()