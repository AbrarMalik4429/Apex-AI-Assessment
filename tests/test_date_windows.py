from datetime import date

import pytest
from sqlalchemy import select

from app.date_windows import add_months
from app.models import Slot
from app.seed import DOCTOR_1, DOCTOR_2
from tests.conftest import intent
from tests.test_booking import send


@pytest.mark.parametrize(
    "start,months,expected",
    [
        (date(2026, 9, 30), 2, date(2026, 11, 30)),
        (date(2026, 12, 31), 2, date(2027, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
    ],
)
def test_calendar_month_addition(start, months, expected):
    assert add_months(start, months) == expected


def test_seed_has_eight_slots_on_five_weekdays_for_each_doctor(harness):
    _, factory, _, _ = harness
    with factory() as db:
        slots = list(db.scalars(select(Slot)))
        assert len(slots) == 80
        for doctor in (DOCTOR_1, DOCTOR_2):
            for weekday in range(7):
                assert sum(s.doctor_id == doctor and s.day_of_week == weekday for s in slots) == (
                    8 if weekday < 5 else 0
                )


def test_specific_date_keeps_date_and_uses_matching_weekday(harness):
    client, factory, fake, _ = harness
    fake.queue.append(intent("book", doctor_query="Amal", appointment_date="2026-10-08"))
    options = send(client).json()["data"]["options"]
    assert len(options) == 8
    with factory() as db:
        for option in options:
            from uuid import UUID

            slot = db.get(Slot, UUID(option["slot_id"]))
            assert option["appointment_date"] == "2026-10-08"
            assert slot.day_of_week == date(2026, 10, 8).weekday()
            assert option["start_time"] == slot.start_time.isoformat()
            assert option["end_time"] == slot.end_time.isoformat()
    fake.queue.append(intent("availability", doctor_query="Amal", appointment_date="2026-10-10"))
    assert send(client).json()["status"] == "unavailable"


def test_range_choices_and_confirmation_keep_displayed_slot(harness):
    client, factory, fake, _ = harness
    fake.queue.append(
        intent("book", doctor_query="Amal", date_from="2026-10-12", date_to="2026-10-23")
    )
    result = send(client).json()
    options = result["data"]["options"]
    assert len(options) == 20
    assert len({(o["slot_id"], o["appointment_date"]) for o in options}) == 20
    for option in options:
        day = date.fromisoformat(option["appointment_date"])
        assert date(2026, 10, 12) <= day <= date(2026, 10, 23)
        assert day.weekday() < 5
    proposal = send(client, "Option 3").json()
    assert proposal["data"]["candidate"] == options[2]
    response = send(client, "confirm", confirmation_token=proposal["confirmation_token"]).json()
    booked = response["data"]["booking"]
    for field in ("slot_id", "appointment_date", "start_time", "end_time"):
        assert booked[field] == options[2][field]


def test_after_two_months_is_calendar_window_and_exact_date_replaces_it(harness):
    client, _, fake, _ = harness
    fake.queue.append(intent("book", doctor_query="Amal", months_after=2))
    result = send(client).json()
    # Harness date is October 5; two calendar months later is December 5.
    assert "2026-12-05 to 2026-12-18" in result["message"]
    assert all(
        "2026-12-05" <= o["appointment_date"] <= "2026-12-18" for o in result["data"]["options"]
    )
    fake.queue.append(intent(appointment_date="2026-12-10"))
    result = send(client).json()
    assert len(result["data"]["options"]) == 8
    assert all(o["appointment_date"] == "2026-12-10" for o in result["data"]["options"])


def test_range_filters_existing_patient_conflicts(harness):
    from tests.test_booking import add_booking

    client, _, fake, _ = harness
    add_booking(harness[1], doctor=DOCTOR_2, day=date(2026, 10, 8))
    fake.queue.append(
        intent("availability", doctor_query="Amal", date_from="2026-10-08", date_to="2026-10-08")
    )
    result = send(client).json()
    assert all(o["start_time"] != "09:00:00" for o in result["data"]["options"])
