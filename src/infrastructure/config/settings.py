from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env.example",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "ChronicCare Nour"
    APP_VERSION: str = "0.1.0-sprint1"
    ENVIRONMENT: Literal["dev", "test", "prod"] = "dev"

    # ==================== LLM ====================
    LLM_PROVIDER: Literal["deepseek", "gemini"] = "deepseek"
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    SQLITE_URL: str = "sqlite+aiosqlite:///./chroniccare.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================== Supabase ====================
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None  # anon / public key (Flutter client)
    SUPABASE_SERVICE_ROLE_KEY: str | None = None  # service-role key (backend, bypasses RLS)


settings = Settings()
