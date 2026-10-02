from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr("")
    backend_url: str = ""
    frontend_url: str = ""
    groq_api_url: str = ""
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    groq_api_key: SecretStr = SecretStr("")
    database_ssl_root_cert: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    groq_response_mode: Literal["strict", "json"] = "strict"
    groq_timeout_seconds: float = Field(default=15, gt=0, le=60)
    clinic_timezone: str = "Asia/Riyadh"
    booking_horizon_days: int = Field(default=90, ge=1, le=365)
    session_hours: int = Field(default=8, ge=1, le=24)
    confirmation_minutes: int = Field(default=10, ge=1, le=30)
    cancellation_notice_hours: int = Field(default=24, ge=0)
    reschedule_notice_hours: int = Field(default=24, ge=0)
    demo_enabled: bool = False

    @field_validator("clinic_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @field_validator("backend_url", "frontend_url", "groq_api_url")
    @classmethod
    def valid_service_url(cls, value: str, info) -> str:
        value = value.strip()
        if not value:
            return value
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.fragment
        ):
            raise ValueError("Use an absolute HTTP(S) URL without credentials or fragments")
        if info.field_name == "groq_api_url" and parts.scheme != "https":
            raise ValueError("The provider endpoint must use HTTPS")
        if info.field_name == "frontend_url" and (parts.path not in {"", "/"} or parts.query):
            raise ValueError("FRONTEND_URL must be an origin without a path or query")
        if info.field_name == "backend_url" and parts.query:
            raise ValueError("API base URLs cannot contain a query")
        return value.rstrip("/")
