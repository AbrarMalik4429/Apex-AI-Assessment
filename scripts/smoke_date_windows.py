"""Live Groq/date-window smoke check; synthetic database writes always roll back."""

import json
from datetime import date, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.date_windows import add_months, default_window_end
from app.db import make_engine
from app.main import create_app
from app.models import Slot, utcnow


def main():
    settings = Settings()
    if not settings.demo_enabled or not settings.groq_api_key.get_secret_value():
        raise SystemExit("Requires synthetic demo mode and Groq configuration.")
    today = utcnow().astimezone(ZoneInfo(settings.clinic_timezone)).date()
    start = today + timedelta(days=7)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    engine = make_engine(settings)
    checks = []
    try:
        with engine.connect() as conn:
            tx = conn.begin()
            try:
                factory = sessionmaker(
                    bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
                )
                with TestClient(create_app(settings, factory)) as client:
                    client.headers["Authorization"] = (
                        "Bearer " + client.post("/demo/session").json()["access_token"]
                    )

                    def say(message, token=None):
                        body = {"request_id": str(uuid4()), "message": message}
                        if token:
                            body["confirmation_token"] = token
                        r = client.post("/assistant/message", json=body)
                        data = r.json()
                        assert r.status_code == 200, data.get("data", {}).get("code")
                        return data

                    windows = [
                        (f"Show Dr. Amal's available slots on {start}", start, start),
                        (
                            f"Book Dr. Amal between {start} and {start + timedelta(days=13)}",
                            start,
                            start + timedelta(days=13),
                        ),
                        (
                            "Book Dr. Amal after two months",
                            add_months(today, 2),
                            default_window_end(
                                add_months(today, 2), today, settings.booking_horizon_days
                            ),
                        ),
                    ]
                    for message, low, high in windows:
                        say("start over")
                        result = say(message)
                        assert result["status"] == "options", result["status"]
                        options = result["data"]["options"]
                        assert options
                        with factory() as db:
                            for option in options:
                                day = date.fromisoformat(option["appointment_date"])
                                slot = db.get(Slot, UUID(option["slot_id"]))
                                assert low <= day <= high
                                assert day.weekday() == slot.day_of_week < 5
                                assert slot.start_time.isoformat() == option["start_time"]
                                assert slot.end_time.isoformat() == option["end_time"]
                        checks.append(
                            {"from": str(low), "to": str(high), "valid_options": len(options)}
                        )
                    selected = options[0]
                    proposal = say("Option 1")
                    assert proposal["status"] == "confirmation_required"
                    confirmed = say("confirm", proposal["confirmation_token"])
                    assert confirmed["status"] == "success"
                    for field in ("slot_id", "appointment_date", "start_time", "end_time"):
                        assert confirmed["data"]["booking"][field] == selected[field]
            finally:
                tx.rollback()
        print(
            json.dumps(
                {
                    "passed": checks,
                    "confirmed_displayed_choice": True,
                    "all_database_writes_rolled_back": True,
                }
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
