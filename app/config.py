from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://postgres:postgres@localhost:5432/booking"
    )
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
