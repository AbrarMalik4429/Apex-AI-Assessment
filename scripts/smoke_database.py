"""Live PostgreSQL booking checks inside one transaction that is always rolled back.

Uses synthetic seeded data and a deterministic interpreter; makes no Groq request.
Run from the backend directory: python -m scripts.smoke_database
"""

import json
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.contracts import Interpretation
from app.db import make_engine
from app.main import create_app
from app.models import Booking, utcnow
from app.seed import DOCTOR_1, DOCTOR_2, FOLLOW_UP_ID, OTHER_PATIENT_ID


class ScriptedInterpreter:
    def __init__(self):
        self.next = None

    def interpret(self, message, context):
        result, self.next = self.next, None
        if result is None:
            raise AssertionError("Unexpected language-model invocation")
        return result

    def set(self, action, **fields):
        values = {name: None for name in Interpretation.model_fields}
        values.update(intent=action, **fields)
        self.next = Interpretation(**values)


def main():
    config = Settings()
    if not config.demo_enabled:
        raise SystemExit("This check requires the synthetic demo configuration.")
    engine = make_engine(config)
    interpreter = ScriptedInterpreter()
    checks = []
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                factory = sessionmaker(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )
                app = create_app(config, factory, interpreter)
                with TestClient(app) as client:
                    session = client.post("/demo/session")
                    assert session.status_code == 201, session.status_code
                    client.headers["Authorization"] = "Bearer " + session.json()["access_token"]
                    checks.append("session creation")
                    day = (utcnow() + timedelta(days=7)).date().isoformat()
                    options = client.get(
                        "/availability",
                        params={"doctor_id": str(DOCTOR_1), "start": day, "end": day},
                    )
                    assert options.status_code == 200
                    slots = options.json()["slots"]
                    assert len(slots) >= 2
                    first, second = slots[:2]
                    checks.append("live availability")

                    def propose(action, slot=None, booking_id=None):
                        fields = {"booking_id": booking_id}
                        if slot:
                            fields.update(
                                doctor_query=slot["doctor_id"],
                                appointment_date=slot["appointment_date"],
                                start_time=slot["start_time"],
                            )
                        interpreter.set(action, **fields)
                        result = client.post(
                            "/assistant/message",
                            json={
                                "request_id": str(uuid4()),
                                "message": "synthetic smoke request " + (booking_id or ""),
                            },
                        )
                        assert result.status_code == 200, result.status_code
                        data = result.json()
                        assert data["status"] == "confirmation_required", data["status"]
                        return {
                            "request_id": str(uuid4()),
                            "message": "confirm",
                            "confirmation_token": data["confirmation_token"],
                        }

                    def confirm(payload):
                        result = client.post("/assistant/message", json=payload)
                        assert result.status_code == 200, result.status_code
                        assert result.json()["status"] == "success", result.json()["status"]
                        return result.json()

                    payload = propose("book", first)
                    booked = confirm(payload)
                    assert confirm(payload) == booked
                    checks.extend(["confirmed booking", "idempotent replay"])
                    old_id = booked["data"]["booking"]["booking_id"]
                    assert booked["data"]["booking"]["slot_id"] == first["slot_id"]
                    with factory() as db:
                        existing = db.get(Booking, UUID(old_id))
                        values = {
                            field: getattr(existing, field)
                            for field in (
                                "doctor_id",
                                "slot_id",
                                "appointment_date",
                                "booked_day_of_week",
                                "booked_start_time",
                                "booked_end_time",
                                "type",
                                "status",
                            )
                        }
                        try:
                            with db.begin_nested():
                                db.add(Booking(patient_id=OTHER_PATIENT_ID, **values))
                                db.flush()
                        except IntegrityError as exc:
                            assert (
                                exc.orig.diag.constraint_name == "uq_bookings_confirmed_slot_date"
                            )
                        else:
                            raise AssertionError("PostgreSQL accepted a duplicate slot/date")
                    checks.append("PostgreSQL rejects another patient's duplicate slot/date")
                    changed = confirm(propose("reschedule", second, old_id))
                    new_id = changed["data"]["booking"]["booking_id"]
                    assert client.get(f"/appointments/{old_id}").json()["status"] == "rescheduled"
                    assert old_id != new_id
                    checks.append("atomic rescheduling")
                    cancelled = confirm(propose("cancel", booking_id=new_id))
                    assert cancelled["data"]["booking"]["status"] == "cancelled"
                    checks.append("cancellation")
                    follow_up = confirm(propose("follow_up", first, str(FOLLOW_UP_ID)))
                    assert follow_up["data"]["booking"]["booking_id"] == str(FOLLOW_UP_ID)
                    checks.append("follow-up scheduling")
                    other = client.get(
                        "/availability",
                        params={"doctor_id": str(DOCTOR_2), "start": day, "end": day},
                    ).json()["slots"]
                    assert first["start_time"] not in [slot["start_time"] for slot in other]
                    checks.append("patient conflicts across doctors")
            finally:
                transaction.rollback()
        print(
            json.dumps(
                {"passed": checks, "all_test_writes_rolled_back": True, "groq_called": False},
                indent=2,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
