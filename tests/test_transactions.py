from uuid import uuid4

from sqlalchemy import event, select
from sqlalchemy.exc import OperationalError

from app.models import Booking
from tests.test_booking import add_booking, propose, send


def test_commit_acknowledgement_lost_replays_saved_result(harness, monkeypatch):
    client, factory, fake, _ = harness
    proposal = propose(client, fake)
    original_commit = factory.class_.commit
    fail = [True]

    def commit_then_lose_ack(db):
        original_commit(db)
        if fail[0]:
            fail[0] = False
            raise OperationalError("COMMIT", {}, Exception("synthetic lost acknowledgement"))

    monkeypatch.setattr(factory.class_, "commit", commit_then_lose_ack)
    request_id = uuid4()
    response = send(
        client, "confirm", request_id, confirmation_token=proposal["confirmation_token"]
    )
    assert response.status_code == 503 and response.json()["status"] == "outcome_unknown"
    retry = send(client, "confirm", request_id, confirmation_token=proposal["confirmation_token"])
    assert retry.json()["status"] == "success"
    with factory() as db:
        assert len(list(db.scalars(select(Booking).where(Booking.status == "confirmed")))) == 1


def test_reschedule_write_error_rolls_back_replacement(harness):
    client, factory, fake, _ = harness
    original = add_booking(factory)
    proposal = propose(client, fake, "reschedule", booking_id=str(original))

    def fail_after_insert(db, flush_context):
        raise OperationalError("INSERT", {}, Exception("synthetic write error"))

    event.listen(factory.class_, "after_flush_postexec", fail_after_insert)
    try:
        response = send(client, "confirm", confirmation_token=proposal["confirmation_token"])
        assert response.status_code == 503
        assert response.json()["status"] == "outcome_unknown"
    finally:
        event.remove(factory.class_, "after_flush_postexec", fail_after_insert)
    with factory() as db:
        assert db.get(Booking, original).status == "confirmed"
        assert len(list(db.scalars(select(Booking).where(Booking.status == "confirmed")))) == 1
