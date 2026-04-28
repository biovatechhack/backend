from openai import AsyncOpenAI
from abstraction.ports.llm_port import LLMProvider
from infrastructure.config.settings import settings
import json
from typing import Dict, Any, List

class DeepSeekAdapter(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        self.model = "deepseek-chat"   # or "deepseek-reasoner" if you want

    async def extract_clinical_entities(self, darija_text: str, glossary: dict) -> Dict[str, Any]:
        system_prompt = f"""You are a clinical NLP engine specialized in Algerian Darija.
You ONLY extract symptoms and context. Return VALID JSON only. No explanation.

Use this glossary to map colloquial Darija → clinical terms:
{json.dumps(glossary, ensure_ascii=False, indent=2)}

Rules:
- Never diagnose.
- Never suggest medication changes.
- Return exactly this schema."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Patient said: {darija_text}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    async def generate_response(self, risk_level: str, symptoms: List[str], patient_context: dict) -> str:
        system_prompt = f"""
        You are Nour, a warm, trusted Algerian digital nurse speaking natural Darija.
        Tone: like a caring family member who is medically knowledgeable. Never alarming.

        Risk level: {risk_level}
        Extracted symptoms: {symptoms}

        Respond in natural Darija. Keep under 70 words.
        If MODERATE risk, ALWAYS end with: "راسلو طبيبك قبل ما تبدل أي دواء أو جرعة.
        """

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate the response to the patient now."}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()