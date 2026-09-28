from sqlalchemy import select

from app.models import Booking
from app.seed import DOCTOR_1
from tests.conftest import intent
from tests.test_booking import add_booking, propose, send


def test_previous_doctor_and_afternoon(harness):
    client, _, fake, _ = harness
    fake.queue.append(
        intent(
            "book",
            doctor_query="previous",
            appointment_date="2026-10-08",
            time_preference="afternoon",
        )
    )
    result = send(client, "Previous doctor, Thursday afternoon").json()
    assert result["status"] == "options"
    assert all(
        o["doctor_id"] == str(DOCTOR_1) and o["start_time"] >= "12:00:00"
        for o in result["data"]["options"]
    )


def test_changed_doctor_invalidates_old_confirmation(harness):
    client, factory, fake, _ = harness
    proposal = propose(client, fake)
    fake.queue.append(intent(doctor_query="Sami"))
    changed = send(client, "Actually Dr. Sami").json()
    assert changed["confirmation_token"] != proposal["confirmation_token"]
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()
    assert result["data"]["code"] == "invalid_confirmation"
    with factory() as db:
        assert not list(db.scalars(select(Booking).where(Booking.status == "confirmed")))


def test_invalid_option_and_model_id(harness):
    client, _, fake, _ = harness
    fake.queue.extend(
        [intent("book"), intent(option_number=99), intent("cancel", booking_id="made-up")]
    )
    assert send(client).json()["status"] == "options"
    assert send(client).json()["data"]["code"] == "invalid_option"
    assert send(client).json()["status"] == "clarification"


def test_cancellation_success_and_already_cancelled(harness):
    client, factory, fake, _ = harness
    booking_id = add_booking(factory)
    fake.queue.append(intent("cancel", booking_id=str(booking_id)))
    proposal = send(client).json()
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()
    assert result["status"] == "success" and result["data"]["booking"]["status"] == "cancelled"
    fake.queue.append(intent("cancel", booking_id=str(booking_id)))
    assert "already cancelled" in send(client).json()["message"]


def test_persisted_state_survives_new_client(harness):
    from fastapi.testclient import TestClient

    client, _, fake, _ = harness
    proposal = propose(client, fake)
    with TestClient(client.app) as second_client:
        second_client.headers["Authorization"] = client.headers["Authorization"]
        result = send(
            second_client, "confirm", confirmation_token=proposal["confirmation_token"]
        ).json()
    assert result["status"] == "success"


def test_reset_makes_proposal_unusable(harness):
    client, _, fake, _ = harness
    proposal = propose(client, fake)
    assert send(client, "reset").json()["status"] == "clarification"
    assert (
        send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()["data"][
            "code"
        ]
        == "invalid_confirmation"
    )


def test_book_option_after_availability_keeps_displayed_choices(harness):
    from tests.conftest import intent
    from tests.test_booking import send

    client, _, fake, _ = harness
    fake.queue.append(intent("availability", doctor_query="Amal", appointment_date="2026-10-08"))
    options = send(client, "Show available times").json()
    assert options["status"] == "options"
    fake.queue.append(intent("book", option_number=1))
    proposal = send(client, "Book the first option").json()
    assert proposal["status"] == "confirmation_required"
    assert proposal["data"]["candidate"]["slot_id"] == options["data"]["options"][0]["slot_id"]


def test_numbered_chat_reply_uses_stored_options_without_model(harness):
    from tests.conftest import intent
    from tests.test_booking import send

    client, _, fake, _ = harness
    fake.queue.append(intent("availability", doctor_query="Amal", appointment_date="2026-10-08"))
    send(client, "Show times")
    result = send(client, "Book option 1").json()
    assert result["status"] == "confirmation_required"
    assert fake.calls == 1
