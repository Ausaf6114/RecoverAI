from typing import Optional
from pydantic import Field, AliasChoices
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
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(
        default="local_synthetic_test_secret_p0_05",
        validation_alias=AliasChoices("RAZORPAY_WEBHOOK_SECRET", "WEBHOOK_SECRET"),
    )

    # SQLite database path — used for webhook_events (Phase 0, backward compat)
    DATABASE_PATH: str = "recoverai.db"

    # SQLAlchemy database URL — Phase 1+
    # Local default: SQLite (file-based, no setup required)
    # Production: set to postgresql+psycopg2://user:password@host/dbname
    DATABASE_URL: str = "sqlite:///recoverai.db"

    # Google Gemini API Key & Model — used by the LLM diagnosis component (Phase 3)
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    GEMINI_MODEL: str = Field(
        default="gemini-3.5-flash",
        validation_alias=AliasChoices("GEMINI_MODEL", "GOOGLE_GEMINI_MODEL"),
    )

    # Razorpay API credentials (read-only; kept backend-side, never exposed to frontend)
    RAZORPAY_KEY_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("RAZORPAY_KEY_ID", "TEST_API_KEY"),
    )
    RAZORPAY_KEY_SECRET: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("RAZORPAY_KEY_SECRET", "TEST_KEY_SECRET"),
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
