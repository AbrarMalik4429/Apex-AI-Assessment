"""Real Groq with a disposable SQLite database; never writes to live Supabase."""

import argparse
import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.db import make_engine, make_session_factory
from app.main import create_app
from app.models import Base, utcnow
from app.seed import seed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    start = parser.parse_args().start
    with TemporaryDirectory() as temp:
        settings = Settings(
            database_url="sqlite:///" + str(Path(temp) / "smoke.db"), demo_enabled=True
        )
        engine = make_engine(settings)
        try:
            Base.metadata.create_all(engine)
            factory = make_session_factory(engine)
            with factory.begin() as db:
                seed(db, settings, utcnow())
            with TestClient(create_app(settings, factory)) as client:
                client.headers["Authorization"] = (
                    "Bearer " + client.post("/demo/session").json()["access_token"]
                )
                cases = [
                    ("What is pre-authorization?", True),
                    ("What does Tawuniya Gold cover?", True),
                    ("Does Bupa cover dental?", True),
                    ("What is the clinic cancellation policy?", True),
                    ("How far ahead can I book?", True),
                    ("What is your clinic address?", None),
                    ("How long should I fast before my blood test?", False),
                ]
                for message, grounded in cases[start:]:
                    payload = {"request_id": str(uuid4()), "message": message}
                    result = client.post("/assistant/message", json=payload)
                    if (
                        result.status_code == 503
                        and result.json().get("data", {}).get("code") == "groq_rate_limited"
                    ):
                        delay = min(60, max(1, int(result.headers.get("Retry-After", "60"))))
                        print(json.dumps({"rate_limit_wait_seconds": delay}), flush=True)
                        time.sleep(delay)
                        result = client.post("/assistant/message", json=payload)
                    body = result.json()
                    print(
                        json.dumps(
                            {
                                "question": message,
                                "http": result.status_code,
                                "status": body.get("status"),
                                "kind": body.get("data", {}).get("kind"),
                                "grounded": body.get("data", {}).get("grounded"),
                                "citations": [
                                    c["chunk_id"] for c in body.get("data", {}).get("citations", [])
                                ],
                                "answer_preview": body.get("message", "")[:250],
                            }
                        ),
                        flush=True,
                    )
                    assert result.status_code == 200
                    assert body["data"].get("kind") == "knowledge"
                    if grounded is None:
                        assert (
                            "not confirm" in body["message"] or "not have enough" in body["message"]
                        )
                    else:
                        assert body["data"].get("grounded") == grounded
                    time.sleep(20)
                print(json.dumps({"passed": len(cases[start:]), "live_database_changed": False}))
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
