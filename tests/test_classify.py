"""Tests the triage call with a stand-in client, so no API calls are made."""

from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from triage.classify import FALLBACK_BETA, triage_email
from triage.models import cost_usd, resolve
from triage.schema import Category, Email, Language, Triage

EMAIL = Email(market="SE", subject="Retur", body="Hur lång tid har jag på mig?")

TRIAGE = Triage(
    language=Language.sv,
    category=Category.return_exchange,
    escalate=False,
    escalate_reason="",
    summary="Asks about the return window.",
    draft_reply="Du har 30 dagar på dig.",
)


class FakeClient:
    """Records the request and returns a canned response, or raises a canned error."""

    def __init__(self, *, stop_reason="end_turn", parsed=TRIAGE, error=None):
        self.request = None
        self._response = SimpleNamespace(
            stop_reason=stop_reason,
            parsed_output=parsed,
            model="claude-opus-5-5",
            usage=SimpleNamespace(
                input_tokens=900, output_tokens=200, cache_read_input_tokens=None, cache_creation_input_tokens=None
            ),
        )
        self._error = error
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def _parse(self, **request):
        self.request = request
        if self._error:
            raise self._error
        return self._response


def test_successful_triage():
    client = FakeClient()
    result = triage_email(client, EMAIL)
    assert result.status == "ok"
    assert result.triage == TRIAGE
    assert result.usage == {
        "input_tokens": 900,
        "output_tokens": 200,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    assert "Hur lång tid har jag på mig?" in client.request["messages"][0]["content"]
    assert client.request["output_format"] is Triage


def test_default_model_gets_effort_and_fallback():
    client = FakeClient()
    triage_email(client, EMAIL, effort="medium")
    assert client.request["output_config"] == {"effort": "medium"}
    assert client.request["fallbacks"] == "default"
    assert client.request["betas"] == [FALLBACK_BETA]


def test_haiku_gets_neither_effort_nor_fallback():
    client = FakeClient()
    triage_email(client, EMAIL, model="claude-haiku-4-5")
    assert "output_config" not in client.request
    assert "fallbacks" not in client.request
    assert "betas" not in client.request


def test_refusal_and_truncation_return_no_triage():
    refused = triage_email(FakeClient(stop_reason="refusal", parsed=None), EMAIL)
    assert (refused.status, refused.triage) == ("refusal", None)
    truncated = triage_email(FakeClient(stop_reason="max_tokens", parsed=None), EMAIL)
    assert (truncated.status, truncated.triage) == ("truncated", None)


def test_connection_failure_is_reported_not_raised():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    result = triage_email(FakeClient(error=anthropic.APIConnectionError(request=request)), EMAIL)
    assert result.status == "error"
    assert result.triage is None
    assert result.error.startswith("connection")


def test_wrong_api_key_stops_the_run():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(401, request=request)
    error = anthropic.AuthenticationError("invalid x-api-key", response=response, body=None)
    with pytest.raises(anthropic.AuthenticationError):
        triage_email(FakeClient(error=error), EMAIL)


def test_cost_uses_reported_tokens_and_list_price():
    usage = {
        "input_tokens": 1_000_000,
        "output_tokens": 100_000,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    assert cost_usd("claude-opus-5-5", usage) == pytest.approx(4.00 + 2.00)
    assert cost_usd("claude-haiku-4-5", usage) == pytest.approx(1.00 + 0.50)
    assert cost_usd("some-other-model", usage) is None


def test_dated_snapshot_id_is_priced_as_its_model():
    usage = {"input_tokens": 1_000_000, "output_tokens": 0}
    assert cost_usd("claude-haiku-4-5-20251001", usage) == pytest.approx(1.00)
    assert resolve("claude-haiku-4-5-20251001") == "claude-haiku-4-5"
    assert resolve("claude-opus-5-5") == "claude-opus-5-5"
    assert resolve("claude-opus-5") is None
