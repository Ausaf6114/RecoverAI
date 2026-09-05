from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "RecoverAI"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Server port — read from environment so cloud platforms (Render, Fly, Railway)
    # can inject the assigned port via the PORT environment variable.
    PORT: int = 8000

    # Razorpay Webhook Secret (separate from API Key Secret)
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None

    # Minimal SQLite database path for Phase 0 event persistence
    DATABASE_PATH: str = "recoverai.db"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
