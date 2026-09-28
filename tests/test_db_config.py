import certifi

from app import db
from app.config import Settings


def capture_engine(monkeypatch, **settings):
    captured = {}

    def fake_create(url, **kwargs):
        captured.update(kwargs)
        return captured

    monkeypatch.setattr(db, "create_engine", fake_create)
    return db.make_engine(Settings(_env_file=None, **settings))


def test_configured_certificate_is_used(monkeypatch):
    result = capture_engine(
        monkeypatch,
        database_url="postgresql+psycopg://example/db?sslmode=verify-full",
        database_ssl_root_cert="certs/supabase-ca.crt",
    )
    assert result["connect_args"]["sslrootcert"] == "certs/supabase-ca.crt"


def test_public_trust_bundle_is_fallback(monkeypatch):
    result = capture_engine(
        monkeypatch, database_url="postgresql+psycopg://example/db?sslmode=verify-full"
    )
    assert result["connect_args"]["sslrootcert"] == certifi.where()


def test_explicit_url_certificate_is_not_overridden(monkeypatch):
    result = capture_engine(
        monkeypatch,
        database_url="postgresql+psycopg://example/db?sslmode=verify-full&sslrootcert=chosen.crt",
        database_ssl_root_cert="other.crt",
    )
    assert "sslrootcert" not in result["connect_args"]
