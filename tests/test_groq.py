import json

import httpx
import pytest

from app.config import Settings
from app.contracts import Interpretation, ProviderError
from app.groq_client import GroqInterpreter
from tests.conftest import intent


def config(**kwargs):
    return Settings(_env_file=None, groq_api_key="synthetic-test-key", **kwargs)


def completion(data=None, finish="stop"):
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": finish,
                    "message": {
                        "content": json.dumps(
                            data or intent("book", doctor_query="Amal").model_dump()
                        )
                    },
                }
            ]
        },
    )


def test_strict_schema_and_fixed_destination():
    def handler(request):
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        payload = json.loads(request.content)
        schema = payload["response_format"]["json_schema"]
        assert schema["strict"] is True
        assert schema["schema"]["additionalProperties"] is False
        assert set(schema["schema"]["required"]) == set(Interpretation.model_fields)
        assert "patient_id" not in schema["schema"]["properties"]
        return completion()

    parsed = GroqInterpreter(config(), httpx.MockTransport(handler)).interpret("book", {})
    assert parsed.intent == "book"


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "groq_authentication_failed"),
        (403, "groq_authentication_failed"),
        (400, "groq_request_rejected"),
        (404, "groq_request_rejected"),
        (302, "groq_request_rejected"),
    ],
)
def test_nonretryable_errors_do_not_echo_response(status, code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="secret upstream detail")

    with pytest.raises(ProviderError) as caught:
        GroqInterpreter(config(), httpx.MockTransport(handler)).interpret("book", {})
    assert caught.value.code == code
    assert "secret" not in str(caught.value)
    assert len(calls) == 1


def test_rate_limit_retry_is_bounded():
    calls, delays = [], []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "1"})

    with pytest.raises(ProviderError) as caught:
        GroqInterpreter(config(), httpx.MockTransport(handler), delays.append).interpret("book", {})
    assert caught.value.code == "groq_rate_limited"
    assert len(calls) == 2 and delays == [1]


def test_long_retry_after_returns_without_sleeping():
    delays = []
    transport = httpx.MockTransport(lambda _: httpx.Response(429, headers={"Retry-After": "60"}))
    with pytest.raises(ProviderError) as caught:
        GroqInterpreter(config(), transport, delays.append).interpret("book", {})
    assert caught.value.retry_after == 60 and not delays


@pytest.mark.parametrize(
    "data",
    [
        {"intent": "execute_sql"},
        {**intent().model_dump(), "patient_id": "other"},
        {**intent().model_dump(), "option_number": "not a number"},
    ],
)
def test_bad_schema_rejected(data):
    with pytest.raises(ProviderError, match="groq_invalid_output"):
        GroqInterpreter(config(), httpx.MockTransport(lambda _: completion(data))).interpret(
            "book", {}
        )


def test_truncated_output_rejected():
    with pytest.raises(ProviderError, match="groq_invalid_output"):
        GroqInterpreter(
            config(), httpx.MockTransport(lambda _: completion(finish="length"))
        ).interpret("book", {})


def test_timeout_is_safe():
    def handler(request):
        raise httpx.ReadTimeout("synthetic timeout", request=request)

    with pytest.raises(ProviderError, match="groq_timeout"):
        GroqInterpreter(config(), httpx.MockTransport(handler)).interpret("book", {})


def test_explicit_json_mode_still_validates():
    def handler(request):
        assert json.loads(request.content)["response_format"] == {"type": "json_object"}
        return completion()

    assert (
        GroqInterpreter(config(groq_response_mode="json"), httpx.MockTransport(handler))
        .interpret("book", {})
        .intent
        == "book"
    )


def test_missing_key_fails_without_network():
    with pytest.raises(ProviderError, match="groq_not_configured"):
        GroqInterpreter(Settings(_env_file=None, groq_api_key="")).interpret("book", {})
