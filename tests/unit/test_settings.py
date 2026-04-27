from __future__ import annotations

from src.infrastructure.config.settings import Settings


def test_default_app_name() -> None:
    s = Settings()
    assert s.APP_NAME == "ChronicCare Nour"


def test_default_app_version() -> None:
    s = Settings()
    assert s.APP_VERSION == "0.1.0-sprint1"


def test_default_environment_is_dev() -> None:
    s = Settings()
    assert s.ENVIRONMENT == "dev"


def test_default_sqlite_url_uses_aiosqlite() -> None:
    s = Settings()
    assert s.SQLITE_URL.startswith("sqlite+aiosqlite://")


def test_default_redis_url() -> None:
    s = Settings()
    assert s.REDIS_URL == "redis://localhost:6379/0"


def test_default_llm_provider_is_deepseek() -> None:
    s = Settings()
    assert s.LLM_PROVIDER == "deepseek"


def test_optional_api_keys_default_to_none() -> None:
    s = Settings()
    assert s.GEMINI_API_KEY is None
    assert s.DEEPSEEK_API_KEY is None


def test_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    s = Settings()
    assert s.ENVIRONMENT == "test"


def test_sqlite_url_override(monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_URL", "sqlite+aiosqlite:///:memory:")
    s = Settings()
    assert s.SQLITE_URL == "sqlite+aiosqlite:///:memory:"
