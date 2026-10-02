from datetime import date, time, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.booking_service import BookingService
from app.contracts import DomainError, ProviderError
from app.models import Booking, Operation, PatientSession, Slot
from app.seed import DOCTOR_1, DOCTOR_2, FOLLOW_UP_ID, OTHER_PATIENT_ID, PATIENT_ID
from tests.conftest import NOW, intent


def send(client, text="message", request_id=None, **kwargs):
    return client.post(
        "/assistant/message",
        json={"request_id": str(request_id or uuid4()), "message": text, **kwargs},
    )


def add_booking(
    factory,
    doctor=DOCTOR_1,
    patient=PATIENT_ID,
    day=date(2026, 10, 8),
    start=time(9),
    end=time(9, 30),
    status="confirmed",
):
    with factory.begin() as db:
        slot = db.scalar(
            select(Slot).where(
                Slot.doctor_id == doctor,
                Slot.day_of_week == day.weekday(),
                Slot.start_time == start,
                Slot.end_time == end,
            )
        )
        if slot is None:
            slot = Slot(doctor_id=doctor, day_of_week=day.weekday(), start_time=start, end_time=end)
            db.add(slot)
            db.flush()
        booking = Booking(
            slot_id=slot.slot_id,
            patient_id=patient,
            doctor_id=doctor,
            appointment_date=day,
            booked_day_of_week=day.weekday(),
            booked_start_time=start,
            booked_end_time=end,
            type="consultation",
            status=status,
        )
        db.add(booking)
        db.flush()
        return booking.booking_id


def propose(client, fake, action="book", **kwargs):
    fake.queue.append(
        intent(
            action, doctor_query="Amal", appointment_date="2026-10-08", start_time="09:00", **kwargs
        )
    )
    result = send(client, "Requested change " + kwargs.get("booking_id", "")).json()
    assert result["status"] == "confirmation_required", result
    return result


def test_patient_conflicts_across_doctors_and_adjacent_allowed(harness):
    client, factory, _, _ = harness
    add_booking(factory, doctor=DOCTOR_2, start=time(9, 15), end=time(9, 45))
    result = client.get(
        "/availability",
        params={"doctor_id": str(DOCTOR_1), "start": "2026-10-08", "end": "2026-10-08"},
    ).json()
    times = [s["start_time"] for s in result["slots"]]
    assert "09:00:00" not in times and "09:30:00" not in times
    assert "10:00:00" in times


def test_doctor_occupancy_and_half_day_leave(harness):
    client, factory, _, _ = harness
    add_booking(
        factory, patient=OTHER_PATIENT_ID, day=date(2026, 10, 9), start=time(10), end=time(10, 30)
    )
    result = client.get(
        "/availability",
        params={"doctor_id": str(DOCTOR_1), "start": "2026-10-09", "end": "2026-10-09"},
    ).json()
    times = [s["start_time"] for s in result["slots"]]
    assert times == ["10:30:00", "11:00:00", "11:30:00", "14:00:00", "14:30:00"]


def test_clarification_selection_confirmation_and_retry(harness):
    client, factory, fake, _ = harness
    fake.queue.extend([intent("book"), intent(option_number=1), intent(option_number=1)])
    doctors = send(client).json()
    assert doctors["data"]["kind"] == "doctor"
    slots = send(client, "first doctor").json()
    assert slots["data"]["kind"] == "slot"
    proposal = send(client, "first time").json()
    assert proposal["status"] == "confirmation_required"
    request_id = uuid4()
    result = send(client, "confirm", request_id, confirmation_token=proposal["confirmation_token"])
    assert result.status_code == 200
    assert result.json()["data"]["booking"]["status"] == "confirmed"
    retry = send(client, "confirm", request_id, confirmation_token=proposal["confirmation_token"])
    assert retry.json() == result.json()
    assert fake.calls == 3  # Confirmation never invokes the model.
    with factory() as db:
        assert len(list(db.scalars(select(Booking).where(Booking.status == "confirmed")))) == 1
    assert send(client, "different input", request_id).status_code == 409


def test_no_mutation_without_confirmation_token(harness):
    client, factory, fake, _ = harness
    propose(client, fake)
    result = send(client, "yes").json()
    assert result["status"] == "clarification"
    with factory() as db:
        assert not list(db.scalars(select(Booking).where(Booking.status == "confirmed")))


def test_stale_selection_is_rechecked(harness):
    client, factory, fake, _ = harness
    proposal = propose(client, fake)
    add_booking(factory, doctor=DOCTOR_2)
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()
    assert result["status"] == "unavailable"


def test_cross_patient_booking_injection_is_rejected(harness):
    client, factory, fake, _ = harness
    other_id = add_booking(factory, patient=OTHER_PATIENT_ID)
    fake.queue.append(intent("cancel", booking_id=str(other_id)))
    response = send(client, f"Cancel another patient's booking {other_id}").json()
    assert response["data"]["code"] == "booking_not_found"
    assert client.get(f"/appointments/{other_id}").json()["code"] == "booking_not_found"
    with factory() as db:
        assert db.get(Booking, other_id).status == "confirmed"


@pytest.mark.parametrize(
    "offset, allowed",
    [
        (timedelta(hours=24), False),
        (timedelta(hours=24, seconds=1), True),
        (timedelta(hours=23), False),
    ],
)
def test_cancellation_boundary(harness, offset, allowed):
    _, factory, _, settings = harness
    start = (NOW + offset).astimezone(__import__("zoneinfo").ZoneInfo(settings.clinic_timezone))
    booking_id = add_booking(
        factory, day=start.date(), start=start.time(), end=(start + timedelta(minutes=30)).time()
    )
    with factory.begin() as db:
        service = BookingService(db, settings, PATIENT_ID, NOW)
        if allowed:
            assert service.cancel(booking_id).status == "cancelled"
        else:
            with pytest.raises(DomainError, match="human approval"):
                service.cancel(booking_id)
            assert db.get(Booking, booking_id).status == "confirmed"


def test_reschedule_replaces_atomically(harness):
    client, factory, fake, _ = harness
    original = add_booking(factory, start=time(10), end=time(10, 30))
    proposal = propose(client, fake, "reschedule", booking_id=str(original))
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()
    assert result["status"] == "success"
    with factory() as db:
        old = db.get(Booking, original)
        assert old.status == "rescheduled"
        assert str(old.superseded_by_booking_id) == result["data"]["booking"]["booking_id"]


def test_failed_reschedule_preserves_old_booking(harness):
    client, factory, fake, _ = harness
    original = add_booking(factory, start=time(10), end=time(10, 30))
    proposal = propose(client, fake, "reschedule", booking_id=str(original))
    add_booking(factory, patient=OTHER_PATIENT_ID)
    response = send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()
    assert response["status"] == "unavailable"
    with factory() as db:
        assert db.get(Booking, original).status == "confirmed"


def test_follow_up_updates_same_record(harness):
    client, factory, fake, _ = harness
    proposal = propose(client, fake, "follow_up", booking_id=str(FOLLOW_UP_ID))
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()
    assert result["data"]["booking"]["booking_id"] == str(FOLLOW_UP_ID)
    with factory() as db:
        assert db.get(Booking, FOLLOW_UP_ID).status == "confirmed"


def test_expired_session_and_confirmation(harness):
    client, factory, fake, _ = harness
    proposal = propose(client, fake)
    with factory.begin() as db:
        session = db.scalar(select(PatientSession))
        state = dict(session.state)
        state["expires_at"] = (NOW - timedelta(seconds=1)).isoformat()
        session.state = state
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()
    assert result["data"]["code"] == "confirmation_expired"
    with factory.begin() as db:
        db.scalar(select(PatientSession)).expires_at = NOW - timedelta(seconds=1)
    assert client.get("/appointments").status_code == 401


def test_provider_failure_has_no_operation_or_booking(harness):
    client, factory, fake, _ = harness
    fake.queue.append(ProviderError("groq_timeout"))
    result = send(client)
    assert result.status_code == 503
    assert result.json()["status"] == "error"
    with factory() as db:
        assert not list(db.scalars(select(Operation)))
        assert not list(db.scalars(select(Booking).where(Booking.status == "confirmed")))


def test_patient_id_not_accepted_and_invalid_dates(harness):
    client, _, fake, _ = harness
    assert send(client, patient_id=str(OTHER_PATIENT_ID)).status_code == 422
    fake.queue.append(intent("book", doctor_query="Amal", appointment_date="not-a-date"))
    assert send(client).json()["status"] == "clarification"
    response = client.get(
        "/availability", params={"doctor_id": str(DOCTOR_1), "start": "2020-01-01"}
    )
    assert response.status_code == 400


def test_cancel_policy_returns_no_fake_escalation(harness):
    client, factory, fake, _ = harness
    booking_id = add_booking(factory, day=date(2026, 10, 5))
    fake.queue.append(intent("cancel", booking_id=str(booking_id)))
    result = send(client, f"Cancel booking {booking_id}").json()
    assert result["status"] == "requires_approval"
    assert "no approval request was submitted" in result["message"]
