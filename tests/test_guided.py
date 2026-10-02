from uuid import uuid4

from app.seed import DOCTOR_1, OTHER_PATIENT_ID
from tests.test_booking import add_booking


def test_guided_booking_confirm_and_replay_without_model(harness):
    client, _, fake, _ = harness
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 404
    body = dict(
        request_id=str(uuid4()),
        action="book",
        doctor_id=str(DOCTOR_1),
        appointment_date="2026-10-08",
        start_time="09:00",
    )
    proposal = client.post("/booking/propose", json=body)
    assert proposal.json()["status"] == "confirmation_required"
    assert client.post("/booking/propose", json=body).json() == proposal.json()
    confirmation = dict(
        request_id=str(uuid4()),
        message="confirm",
        confirmation_token=proposal.json()["confirmation_token"],
    )
    booked = client.post("/assistant/message", json=confirmation)
    assert booked.json()["status"] == "success"
    assert client.post("/assistant/message", json=confirmation).json() == booked.json()
    assert fake.calls == 0


def test_guided_rejects_patient_override_and_foreign_booking(harness):
    client, factory, fake, _ = harness
    booking_id = add_booking(factory, patient=OTHER_PATIENT_ID)
    body = dict(request_id=str(uuid4()), action="cancel", booking_id=str(booking_id))
    assert client.post("/booking/propose", json=body).json()["data"]["code"] == "booking_not_found"
    body["patient_id"] = str(OTHER_PATIENT_ID)
    assert client.post("/booking/propose", json=body).status_code == 422
    client.headers.pop("Authorization")
    assert (
        client.post(
            "/booking/propose", json=dict(request_id=str(uuid4()), action="book")
        ).status_code
        == 401
    )
    assert fake.calls == 0


def test_guided_reschedule_cancel_and_followup(harness):
    client, _, fake, _ = harness
    from app.seed import FOLLOW_UP_ID

    def change(action, booking_id=None, start="09:00"):
        body = dict(
            request_id=str(uuid4()),
            action=action,
            doctor_id=str(DOCTOR_1),
            appointment_date="2026-10-08",
            start_time=start,
            booking_id=booking_id,
        )
        proposal = client.post("/booking/propose", json=body).json()
        assert proposal["status"] == "confirmation_required"
        result = client.post(
            "/assistant/message",
            json=dict(
                request_id=str(uuid4()),
                message="confirm",
                confirmation_token=proposal["confirmation_token"],
            ),
        ).json()
        assert result["status"] == "success"
        return result["data"]["booking"]

    booked = change("book")
    moved = change("reschedule", booked["booking_id"], "10:00")
    assert moved["start_time"] == "10:00:00"
    assert change("cancel", moved["booking_id"])["status"] == "cancelled"
    assert change("follow_up", str(FOLLOW_UP_ID))["booking_id"] == str(FOLLOW_UP_ID)
    assert fake.calls == 0
