from datetime import date

from sqlalchemy import select

from app.models import Booking
from app.seed import FOLLOW_UP_ID, OTHER_PATIENT_ID, PARENT_ID, PATIENT_ID
from tests.conftest import intent
from tests.test_booking import add_booking, send


def test_active_appointments_hide_history_and_other_patients(harness):
    client, factory, fake, _ = harness
    active = add_booking(factory)
    for status in ("cancelled", "rescheduled", "completed", "no_show"):
        add_booking(factory, status=status)
    add_booking(factory, patient=OTHER_PATIENT_ID, day=date(2026, 10, 15))
    result = client.get("/appointments").json()["appointments"]
    assert {b["booking_id"] for b in result} == {str(active), str(FOLLOW_UP_ID)}
    fake.queue.append(intent("appointments"))
    chat = send(client, "Show my appointments").json()
    assert {b["booking_id"] for b in chat["data"]["appointments"]} == {
        str(active),
        str(FOLLOW_UP_ID),
    }
    fake.queue.append(intent("appointments", booking_id=str(PARENT_ID)))
    assert send(client, f"Look up {PARENT_ID}").json()["data"]["appointments"] == []
    with factory() as db:
        assert len(list(db.scalars(select(Booking)))) == 8


def test_only_replacement_is_listed_after_reschedule(harness):
    client, factory, fake, _ = harness
    original = add_booking(factory)
    from app.booking_service import BookingService
    from tests.conftest import NOW

    with factory.begin() as db:
        service = BookingService(
            db, harness[3], PATIENT_ID, NOW
        )
        old = service.lookup(original)
        choices = service.availability(old.doctor_id, date(2026, 10, 15), date(2026, 10, 15))
        new = service.reschedule(original, choices[0])
        new_id = new.booking_id
    ids = {b["booking_id"] for b in client.get("/appointments").json()["appointments"]}
    assert str(original) not in ids
    assert str(new_id) in ids
