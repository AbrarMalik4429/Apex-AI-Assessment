"""Opt-in real Groq + PostgreSQL conversation checks; database writes roll back.

Run with synthetic demo data only: python -m scripts.smoke_chat
This makes paid/rate-limited Groq requests. Never prints keys or session tokens.
"""

import json
from datetime import timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import make_engine
from app.main import create_app
from app.models import utcnow
from app.seed import FOLLOW_UP_ID


def main():
    settings = Settings()
    if not settings.demo_enabled or not settings.groq_api_key.get_secret_value():
        raise SystemExit("Requires synthetic demo mode and a configured Groq key.")
    engine = make_engine(settings)
    checks = []
    try:
        with engine.connect() as connection:
            outer = connection.begin()
            try:
                factory = sessionmaker(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )
                with TestClient(create_app(settings, factory)) as client:
                    token = client.post("/demo/session").json()["access_token"]
                    client.headers["Authorization"] = "Bearer " + token

                    def say(message, confirmation=None):
                        body = {"request_id": str(uuid4()), "message": message}
                        if confirmation:
                            body["confirmation_token"] = confirmation
                        response = client.post("/assistant/message", json=body)
                        result = response.json()
                        if response.status_code != 200:
                            raise AssertionError(
                                result.get("data", {}).get("code", "request_failed")
                            )
                        return result

                    def confirm(proposal):
                        assert proposal["status"] == "confirmation_required", proposal["status"]
                        result = say("confirm", proposal["confirmation_token"])
                        assert result["status"] == "success", result["status"]
                        return result["data"]["booking"]

                    day = (
                        (
                            utcnow().astimezone(ZoneInfo(settings.clinic_timezone))
                            + timedelta(days=7)
                        )
                        .date()
                        .isoformat()
                    )
                    options = say(f"Show available appointments with Dr. Amal on {day}")
                    assert options["status"] == "options", options["status"]
                    first, second = options["data"]["options"][:2]
                    checks.append("natural-language availability")
                    booked = confirm(say("Book option 1"))
                    checks.append("option selection and confirmed booking")
                    found = say("Show my appointments")
                    assert any(
                        b["booking_id"] == booked["booking_id"]
                        for b in found["data"]["appointments"]
                    )
                    checks.append("appointment lookup")
                    moved = confirm(
                        say(
                            f"Reschedule appointment {booked['booking_id']} to {second['appointment_date']} at {second['start_time']}"
                        )
                    )
                    assert moved["start_time"] == second["start_time"]
                    checks.append("reschedule")
                    cancelled = confirm(say(f"Cancel appointment {moved['booking_id']}"))
                    assert cancelled["status"] == "cancelled"
                    checks.append("cancellation")
                    followup = confirm(
                        say(
                            f"Schedule my follow-up {FOLLOW_UP_ID} on {first['appointment_date']} at {first['start_time']}"
                        )
                    )
                    assert followup["booking_id"] == str(FOLLOW_UP_ID)
                    checks.append("follow-up scheduling")
            finally:
                outer.rollback()
        print(
            json.dumps(
                {"passed": checks, "real_groq": True, "all_database_writes_rolled_back": True}
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
