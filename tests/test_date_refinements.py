from tests.conftest import intent
from tests.test_booking import send


def test_sequential_week_day_weekday_and_unavailable(harness):
    client, _, fake, _ = harness

    def ask(text, **fields):
        fake.queue.append(intent(**fields))
        return send(client, text).json()

    first = ask("Book Amal two weeks later", action="book", doctor_query="Amal", days_after=14)
    assert all(o["appointment_date"] == "2026-10-19" for o in first["data"]["options"])
    later = ask("Can I have a day later?", shift_days=1)
    assert all(o["appointment_date"] == "2026-10-20" for o in later["data"]["options"])
    thursday = ask("What about Thursday?", requested_weekday=3)
    assert all(o["appointment_date"] == "2026-10-22" for o in thursday["data"]["options"])
    weekend = ask("What about Saturday?", requested_weekday=5)
    assert weekend["status"] == "unavailable"
    assert "2026-10-24" in weekend["message"]
    monday = ask("Then Monday?", requested_weekday=0)
    assert all(o["appointment_date"] == "2026-10-26" for o in monday["data"]["options"])


def test_selected_range_date_becomes_refinement_anchor(harness):
    client, _, fake, _ = harness
    fake.queue.append(
        intent("book", doctor_query="Amal", date_from="2026-10-12", date_to="2026-10-23")
    )
    options = send(client).json()["data"]["options"]
    index = next(
        i
        for i, o in enumerate(options)
        if __import__("datetime").date.fromisoformat(o["appointment_date"]).weekday() < 4
    )
    chosen = send(client, f"Option {index + 1}").json()
    fake.queue.append(intent(shift_days=1))
    revised = send(client, "A day later please").json()
    from datetime import date, timedelta

    expected = (
        date.fromisoformat(chosen["data"]["candidate"]["appointment_date"]) + timedelta(days=1)
    ).isoformat()
    assert revised["status"] == "options"
    assert all(o["appointment_date"] == expected for o in revised["data"]["options"])
    assert revised["confirmation_token"] is None


def test_weekday_filter_within_range_and_missing_anchor(harness):
    from datetime import date

    client, _, fake, _ = harness
    fake.queue.append(intent(shift_days=1))
    assert send(client, "A day later").json()["status"] == "clarification"
    fake.queue.append(
        intent("book", doctor_query="Amal", date_from="2026-10-12", date_to="2026-10-23")
    )
    send(client)
    fake.queue.append(intent(requested_weekday=3))
    options = send(client, "Thursday please").json()["data"]["options"]
    assert len(options) == 16
    assert all(date.fromisoformat(o["appointment_date"]).weekday() == 3 for o in options)
