from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    confirmation_token: str | None = Field(default=None, max_length=128)


class Interpretation(BaseModel):
    """All fields required, nullable values: compatible with Groq strict JSON schema."""

    model_config = ConfigDict(extra="forbid", strict=True)
    intent: Literal[
        "book",
        "availability",
        "reschedule",
        "cancel",
        "follow_up",
        "appointments",
        "continue",
        "unknown",
    ]
    doctor_query: str | None
    specialty: str | None
    appointment_date: str | None
    date_from: str | None
    date_to: str | None
    months_after: int | None = Field(ge=0, le=12)
    days_after: int | None = Field(ge=0, le=365)
    shift_days: int | None = Field(ge=-365, le=365)
    requested_weekday: int | None = Field(ge=0, le=6)
    start_time: str | None
    booking_id: str | None
    option_number: int | None
    appointment_type: str | None
    time_preference: Literal["morning", "afternoon", "evening"] | None


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doctor_id: UUID
    doctor_name: str
    slot_id: UUID
    appointment_date: date
    start_time: time
    end_time: time


class AssistantResponse(BaseModel):
    request_id: UUID
    status: Literal[
        "clarification",
        "options",
        "confirmation_required",
        "success",
        "requires_approval",
        "unavailable",
        "error",
        "outcome_unknown",
    ]
    message: str
    data: dict = Field(default_factory=dict)
    confirmation_token: str | None = None


class DomainError(Exception):
    def __init__(self, code: str, message: str, status: str = "error"):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class ProviderError(Exception):
    def __init__(self, code: str, retry_after: int | None = None):
        self.code = code
        self.retry_after = retry_after
        super().__init__(code)


class GuidedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    action: Literal["book", "reschedule", "cancel", "follow_up"]
    doctor_id: UUID | None = None
    appointment_date: date | None = None
    start_time: time | None = None
    booking_id: UUID | None = None
