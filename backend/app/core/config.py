from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]  # -> backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "BrainFlow AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'brainflow.db'}"

    SCHEDULER_ENABLED: bool = True
    SCAN_INTERVAL_MINUTES: int = 5

    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    NAGER_DATE_BASE_URL: str = "https://date.nager.at/api/v3"
    EXTERNAL_TIMEOUT_SECONDS: float = 6.0
    PUBLIC_HOLIDAY_COUNTRY: str = "ET"

    ADMIN_USERNAME: str = "admin"
    ADMIN_DISPLAY_NAME: str = "Admin"
    ADMIN_PASSWORD: str = "BrainFlow@2026"
    SESSION_TTL_HOURS: int = 8
    SESSION_COOKIE_NAME: str = "brainflow_session"
    COOKIE_SECURE: bool = False  # True in production with HTTPS

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT_SECONDS: float = 20.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
