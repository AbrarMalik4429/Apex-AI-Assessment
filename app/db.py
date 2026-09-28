import certifi
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import Settings


def make_engine(settings: Settings):
    url = settings.database_url.get_secret_value()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("sqlite"):
        # Test-only backend. Production uses PostgreSQL and migrations.
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            execution_options={"schema_translate_map": {"booking": None}},
        )
    connect_args = {"connect_timeout": 5, "options": "-c statement_timeout=10000"}
    if make_url(url).query.get("sslmode") == "verify-full":
        if "sslrootcert" not in make_url(url).query:
            connect_args["sslrootcert"] = settings.database_ssl_root_cert or certifi.where()
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        connect_args=connect_args,
    )


def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
