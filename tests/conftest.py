import os
import runpy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from app.config import Settings
from app.contracts import Interpretation
from app.db import make_engine, make_session_factory
from app.main import create_app
from app.models import Base
from app.seed import seed

NOW = datetime(2026, 10, 5, 5, 0, tzinfo=timezone.utc)  # Monday 08:00 Riyadh


def intent(action="continue", **kwargs):
    data = {field: None for field in Interpretation.model_fields}
    data.update(intent=action, **kwargs)
    return Interpretation(**data)


class FakeInterpreter:
    def __init__(self):
        self.queue = []
        self.calls = 0

    def interpret(self, message, context):
        self.calls += 1
        result = self.queue.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def harness(tmp_path):
    postgres_url = os.environ.get("TEST_DATABASE_URL")
    settings = Settings(
        _env_file=None,
        database_url=postgres_url or f"sqlite:///{tmp_path / 'test.db'}",
        demo_enabled=True,
    )
    engine = make_engine(settings)
    schema = None
    if postgres_url:
        schema = "booking_test_" + uuid4().hex
        ddl = Path("migrations/versions/0001_initial.sql").read_text(encoding="utf-8")
        ddl = ddl.replace("SCHEMA booking", "SCHEMA " + schema).replace("booking.", schema + ".")
        with engine.begin() as connection:
            for statement in ddl.split(";"):
                if statement.strip():
                    connection.execute(text(statement))
            migration = runpy.run_path(
                "migrations/versions/603768ba3dac_booking_slot_date_uniqueness.py"
            )
            for statement in migration["UPGRADE_SQL"]:
                connection.execute(text(statement.replace("booking.", schema + ".")))
        engine = engine.execution_options(schema_translate_map={"booking": schema})
    else:

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory.begin() as db:
        seed(db, settings, NOW)
    interpreter = FakeInterpreter()
    app = create_app(settings, factory, interpreter, clock=lambda: NOW)
    try:
        with TestClient(app) as client:
            token = client.post("/demo/session").json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"
            yield client, factory, interpreter, settings
    finally:
        if schema:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
