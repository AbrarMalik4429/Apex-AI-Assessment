"""Real Groq, disposable local database: sequential date-refinement smoke test."""

import json
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.config import Settings
from app.db import make_engine, make_session_factory
from app.main import create_app
from app.models import Base, utcnow
from app.seed import seed


def main():
    now = utcnow()
    with TemporaryDirectory() as temp:
        settings = Settings(
            database_url="sqlite:///" + str(Path(temp) / "demo.db"), demo_enabled=True
        )
        engine = make_engine(settings)
        try:
            Base.metadata.create_all(engine)
            factory = make_session_factory(engine)
            with factory.begin() as db:
                seed(db, settings, now)
            with TestClient(create_app(settings, factory, clock=lambda: now)) as client:
                client.headers["Authorization"] = (
                    "Bearer " + client.post("/demo/session").json()["access_token"]
                )
                day = now.astimezone(ZoneInfo(settings.clinic_timezone)).date() + timedelta(days=14)
                cases = [("Book Dr. Amal two weeks later", day)]
                day += timedelta(days=1)
                cases.append(("Can you give me a day later?", day))
                day += timedelta(days=(3 - day.weekday()) % 7)
                cases.append(("Can you give me Thursday instead?", day))
                day += timedelta(days=(5 - day.weekday()) % 7)
                cases.append(("How about Saturday?", day))
                day += timedelta(days=(0 - day.weekday()) % 7)
                cases.append(("Then Monday please", day))
                passed = []
                for message, expected in cases:
                    r = client.post(
                        "/assistant/message", json={"request_id": str(uuid4()), "message": message}
                    )
                    result = r.json()
                    assert r.status_code == 200, result.get("data", {}).get("code")
                    if expected.weekday() >= 5:
                        assert result["status"] == "unavailable", result["status"]
                        assert str(expected) in result["message"]
                    else:
                        assert result["status"] == "options", result["status"]
                        assert all(
                            o["appointment_date"] == str(expected)
                            for o in result["data"]["options"]
                        ), result["message"]
                    passed.append(
                        {"message": message, "date": str(expected), "status": result["status"]}
                    )
                print(json.dumps({"passed": passed, "live_database_changed": False}))
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
