from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
import os
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",           # still useful for teammates
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

    APP_NAME: str = "ChronicCare Nour"
    APP_VERSION: str = "0.1.0-sprint1"
    ENVIRONMENT: Literal["dev", "test", "prod"] = "dev"

    # ==================== LLM ====================
    LLM_PROVIDER: Literal["deepseek", "gemini"] = "deepseek"
    DEEPSEEK_API_KEY: str | None = None                        # Pydantic reads from OS env var automatically
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    
    # Gemini fallback (your friend will use later)
    GEMINI_API_KEY: str | None = None

    # ==================== Other infra ====================
    SQLITE_URL: str = "sqlite+aiosqlite:///./chroniccare.db"
    REDIS_URL: str = "redis://localhost:6379/0"

settings = Settings()  # ← singleton, use everywhere