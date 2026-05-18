from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Union
from pydantic import field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str
    API_V1_STR: str

    # ─── Auth & Security ─────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY: str

    # ─── Database (PostgreSQL) ───────────────────────────
    DATABASE_URL: str

    # ─── Firebase ─────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str
    FIREBASE_PROJECT_ID: str

    # ─── SMTP (Email) ─────────────────────────────────────
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_NAME: str
    SMTP_FROM_EMAIL: str

    # ─── Google Translate API ─────────────────────────────
    GOOGLE_TRANSLATE_API_KEY: str

    # ─── Redis + Celery ──────────────────────────────────
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # ─── CORS ─────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
