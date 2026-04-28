from __future__ import annotations

import json
import logging

from google import genai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.abstraction.ports.llm_port import LlmPort
from src.domain.exceptions import GeminiParseError, GeminiUnavailableError
from src.domain.models.llm_models import EntityExtractionResult
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_ENTITY_PROMPT = """\
You are a clinical NLP system. Extract medical entities from the patient message below.
Return ONLY a JSON object with these keys:
  medications (list[str]), symptoms (list[str]),
  vital_signs (dict[str,str]), risk_flags (list[str]).

Patient message:
{text}
"""


class GeminiClient(LlmPort):
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY must be set to use GeminiClient")
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(GeminiUnavailableError),
        reraise=True,
    )
    async def _call(self, prompt: str) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            return response.text  # type: ignore[no-any-return]
        except Exception as exc:
            logger.warning("Gemini API error: %s", exc)
            raise GeminiUnavailableError(str(exc)) from exc

    async def extract_entities(self, conversation_text: str) -> EntityExtractionResult:
        raw = await self._call(_ENTITY_PROMPT.format(text=conversation_text))
        cleaned = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        try:
            return EntityExtractionResult.model_validate(json.loads(cleaned))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Cannot parse Gemini entity extraction: %r", raw)
            raise GeminiParseError(f"Cannot parse: {raw!r}") from exc

    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        return await self._call(f"{system_prompt}\n\nUser: {user_message}")
