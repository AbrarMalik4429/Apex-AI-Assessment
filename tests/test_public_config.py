import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


def test_api_only_routes_and_exact_frontend_cors(harness):
    _, factory, fake, _ = harness
    settings = Settings(
        _env_file=None,
        frontend_url="https://portal.example.test",
        groq_api_url="https://provider.example.test/completions",
        groq_api_key="secret-provider-key",
        database_url="secret-database-value",
    )
    with TestClient(create_app(settings, factory, fake)) as client:
        assert client.get("/").json()["service"] == "Apex booking API"
        assert client.get("/frontend-config.js").status_code == 404
        assert client.get("/static/app.js").status_code == 404
        headers = {
            "Origin": "https://portal.example.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        }
        allowed = client.options("/assistant/message", headers=headers)
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == headers["Origin"]
        headers["Origin"] = "https://unrelated.example.test"
        assert client.options("/assistant/message", headers=headers).status_code == 400


def test_provider_endpoint_requires_https():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, groq_api_url="http://provider.example.test/completions")


def test_custom_provider_url_is_used_without_redirects():
    import httpx

    from app.groq_client import GroqInterpreter
    from tests.conftest import intent

    def handler(request):
        assert str(request.url) == "https://provider.example.test/custom/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": intent("book").model_dump_json()},
                    }
                ]
            },
        )

    config = Settings(
        _env_file=None,
        groq_api_key="synthetic",
        groq_api_url="https://provider.example.test/custom/completions",
    )
    assert (
        GroqInterpreter(config, httpx.MockTransport(handler)).interpret("book", {}).intent == "book"
    )
