"""Notice-policy regression tests using a controlled clock and persisted bookings."""

from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.booking_service import BookingService
from app.contracts import DomainError
from app.main import create_app
from app.models import Booking
from app.seed import DOCTOR_1, PATIENT_ID
from tests.conftest import NOW, intent
from tests.test_booking import add_booking, send


@pytest.mark.parametrize("seconds,allowed", [(86399, False), (86400, False), (86401, True)])
def test_reschedule_notice_uses_original_start(harness, seconds, allowed):
    _, factory, _, settings = harness
    start = (NOW + timedelta(seconds=seconds)).astimezone(ZoneInfo(settings.clinic_timezone))
    original = add_booking(
        factory, day=start.date(), start=start.time(), end=(start + timedelta(minutes=30)).time()
    )
    with factory.begin() as db:
        before = set(db.scalars(select(Booking.booking_id)))
        service = BookingService(db, settings, PATIENT_ID, NOW)
        # A distant replacement must not bypass the original appointment's notice period.
        target = service.availability(DOCTOR_1, date(2026, 10, 12), date(2026, 10, 12))[0]
        if allowed:
            replacement = service.reschedule(original, target)
            assert replacement.status == "confirmed"
            assert replacement.appointment_date == date(2026, 10, 12)
            assert db.get(Booking, original).superseded_by_booking_id == replacement.booking_id
            assert db.get(Booking, original).status == "rescheduled"
            assert set(db.scalars(select(Booking.booking_id))) == before | {replacement.booking_id}
        else:
            with pytest.raises(DomainError) as error:
                service.reschedule(original, target)
            assert error.value.code == "notice_policy"
            assert error.value.status == "requires_approval"
            assert db.get(Booking, original).status == "confirmed"
            assert db.get(Booking, original).superseded_by_booking_id is None
            assert set(db.scalars(select(Booking.booking_id))) == before


@pytest.mark.parametrize("action", ["cancel", "reschedule"])
def test_confirmation_rechecks_notice_after_clock_crosses_boundary(harness, action):
    first_client, factory, fake, settings = harness
    original = add_booking(factory, day=date(2026, 10, 6), start=time(9), end=time(9, 30))
    clock = [NOW + timedelta(minutes=58)]  # Monday 08:58 Riyadh: 24h02m before start.
    app = create_app(settings, factory, fake, clock=lambda: clock[0])
    fields = {"booking_id": str(original)}
    if action == "reschedule":
        fields.update(appointment_date="2026-10-08", start_time="09:00")
    fake.queue.append(intent(action, **fields))
    with TestClient(app) as client:
        client.headers["Authorization"] = first_client.headers["Authorization"]
        proposal = send(client, f"Requested change for {original}").json()
        assert proposal["status"] == "confirmation_required"
        with factory() as db:
            before = set(db.scalars(select(Booking.booking_id)))
        clock[0] += timedelta(minutes=3)  # Token remains valid, but notice is now 23h59m.
        result = send(client, "confirm", confirmation_token=proposal["confirmation_token"])
        assert result.status_code == 200
        assert result.json()["status"] == "requires_approval"
        assert result.json()["data"]["code"] == "notice_policy"
        assert result.json()["confirmation_token"] is None
        assert "no approval request was submitted" in result.json()["message"]
        assert fake.calls == 1  # Confirmation is deterministic, with no second model call.
    with factory() as db:
        booking = db.get(Booking, original)
        assert booking.status == "confirmed"
        assert booking.superseded_by_booking_id is None
        assert booking.appointment_date == date(2026, 10, 6)
        assert set(db.scalars(select(Booking.booking_id))) == before


@pytest.mark.parametrize("blocked_action", ["cancel", "reschedule"])
def test_cancellation_and_rescheduling_have_independent_thresholds(harness, blocked_action):
    _, factory, _, settings = harness
    settings = settings.model_copy(update={
        "cancellation_notice_hours": 48 if blocked_action == "cancel" else 24,
        "reschedule_notice_hours": 48 if blocked_action == "reschedule" else 24,
    })
    start = (NOW + timedelta(hours=30)).astimezone(ZoneInfo(settings.clinic_timezone))
    original = add_booking(
        factory, day=start.date(), start=start.time(), end=(start + timedelta(minutes=30)).time()
    )
    with factory.begin() as db:
        service = BookingService(db, settings, PATIENT_ID, NOW)
        booking = db.get(Booking, original)
        with pytest.raises(DomainError) as error:
            service.check_change(booking, blocked_action)
        assert error.value.code == "notice_policy"
        service.check_change(booking, "reschedule" if blocked_action == "cancel" else "cancel")
        assert booking.status == "confirmed"
