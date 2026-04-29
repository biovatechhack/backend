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
        """LLM Call 1: Strict symptom extraction with standardised dimension tracking."""
        glossary = load_glossary()

        system_prompt = f"""You are a clinical NLP engine specialised in Algerian Darija.
Return ONLY valid JSON. Never add explanation or markdown.

Darija medical glossary (use for normalisation):
{json.dumps(glossary, ensure_ascii=False)}

Analyse the patient message and return EXACTLY this JSON structure:
{{
  "symptoms": ["list of normalised clinical symptom names in English"],
  "severity_hints": ["descriptors like mild/moderate/severe/خفيف/شديد"],
  "missing_fields": ["list of dimensions NOT mentioned by the patient — choose ONLY from these exact values: chief_complaint, onset, duration, severity, associated_symptoms, aggravating_factors, context"],
  "darija_confidence": 0.0
}}

Dimension definitions (to decide what is 'missing'):
- chief_complaint: the main symptom or problem the patient is describing
- onset: when the symptoms first started (today, yesterday, a week ago…)
- duration: how long the symptoms have been present
- severity: intensity (mild, moderate, severe, scale 1-10, or Darija equivalents)
- associated_symptoms: any other symptoms mentioned alongside the main one
- aggravating_factors: what makes the symptoms worse
- context: recent meals, medication taken today, physical activity level

RULE: if a dimension is clearly stated in the message → do NOT include it in missing_fields.
darija_confidence: float 0.0-1.0 reflecting how confident you are the text is Darija."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Patient message: {conversation_text}"}
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