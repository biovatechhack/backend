from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.exceptions import GeminiParseError, GeminiUnavailableError
from src.domain.models.llm_models import EntityExtractionResult
from src.infrastructure.intelligence.gemini_client import GeminiClient


def _make_client() -> GeminiClient:
    """Return a GeminiClient with mocked genai internals."""
    with (
        patch(
            "src.infrastructure.intelligence.gemini_client.genai.Client",
            return_value=MagicMock(),
        ),
        patch(
            "src.infrastructure.intelligence.gemini_client.settings",
            GEMINI_API_KEY="fake-key",
            GEMINI_MODEL="gemini-2.0-flash",
        ),
    ):
        return GeminiClient()


def _set_response(client: GeminiClient, text: str) -> None:
    client._client.aio.models.generate_content = AsyncMock(  # type: ignore[attr-defined]
        return_value=MagicMock(text=text)
    )


def _set_error(client: GeminiClient, exc: Exception) -> None:
    client._client.aio.models.generate_content = AsyncMock(  # type: ignore[attr-defined]
        side_effect=exc
    )


# ── construction ──────────────────────────────────────────────────────────────

def test_init_raises_without_api_key() -> None:
    with (
        patch("src.infrastructure.intelligence.gemini_client.settings", GEMINI_API_KEY=None),
        pytest.raises(RuntimeError, match="GEMINI_API_KEY"),
    ):
        GeminiClient()


def test_init_succeeds_with_api_key() -> None:
    client = _make_client()
    assert isinstance(client, GeminiClient)


# ── extract_entities ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_entities_returns_parsed_result() -> None:
    payload = {
        "medications": ["metformin"],
        "symptoms": ["fatigue"],
        "vital_signs": {"glucose": "9.0 mmol/L"},
        "risk_flags": [],
    }
    client = _make_client()
    _set_response(client, json.dumps(payload))

    result = await client.extract_entities("I take metformin and feel fatigued.")
    assert isinstance(result, EntityExtractionResult)
    assert result.medications == ["metformin"]
    assert result.symptoms == ["fatigue"]
    assert result.vital_signs == {"glucose": "9.0 mmol/L"}


@pytest.mark.asyncio
async def test_extract_entities_strips_markdown_fences() -> None:
    payload = {"medications": [], "symptoms": ["dizziness"], "vital_signs": {}, "risk_flags": []}
    client = _make_client()
    _set_response(client, f"```json\n{json.dumps(payload)}\n```")

    result = await client.extract_entities("I feel dizzy")
    assert result.symptoms == ["dizziness"]


@pytest.mark.asyncio
async def test_extract_entities_raises_parse_error_on_bad_json() -> None:
    client = _make_client()
    _set_response(client, "not valid json at all")

    with pytest.raises(GeminiParseError):
        await client.extract_entities("some message")


@pytest.mark.asyncio
async def test_extract_entities_raises_unavailable_after_retries() -> None:
    client = _make_client()
    _set_error(client, RuntimeError("connection refused"))

    with pytest.raises(GeminiUnavailableError):
        await client.extract_entities("some message")


# ── generate_response ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_response_returns_text() -> None:
    client = _make_client()
    _set_response(client, "Take your medication after meals.")

    reply = await client.generate_response(
        system_prompt="You are a chronic-care assistant.",
        user_message="When should I take metformin?",
    )
    assert reply == "Take your medication after meals."


@pytest.mark.asyncio
async def test_generate_response_includes_system_prompt_in_call() -> None:
    client = _make_client()
    captured: list[str] = []

    async def _fake_generate(**kwargs: object) -> MagicMock:
        captured.append(str(kwargs.get("contents", "")))
        return MagicMock(text="ok")

    client._client.aio.models.generate_content = _fake_generate  # type: ignore[attr-defined]

    await client.generate_response("SYS", "USR")
    assert "SYS" in captured[0]
    assert "USR" in captured[0]


@pytest.mark.asyncio
async def test_generate_response_raises_unavailable_after_retries() -> None:
    client = _make_client()
    _set_error(client, Exception("timeout"))

    with pytest.raises(GeminiUnavailableError):
        await client.generate_response("sys", "usr")
