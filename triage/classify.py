import time
from dataclasses import dataclass, field
from typing import Literal

import anthropic

from .models import DEFAULT_MODEL, MODELS
from .prompt import SYSTEM_PROMPT, render_email
from .schema import Email, Triage

# If the model declines a request, the API reruns it on another model in the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

Status = Literal["ok", "refusal", "truncated", "error"]


def make_client() -> anthropic.Anthropic:
    """Client with a cap on how long one email can take. Exits early when no credentials are set."""
    client = anthropic.Anthropic(timeout=120.0, max_retries=3)
    if client.api_key is None and client.auth_token is None and client.credentials is None:
        raise SystemExit("No API credentials found. Set ANTHROPIC_API_KEY and try again.")
    return client


@dataclass
class TriageResult:
    """Outcome for one email. Anything other than "ok" means the email stays with a person."""

    status: Status
    triage: Triage | None
    model_requested: str
    model_served: str | None = None
    usage: dict = field(default_factory=dict)
    latency_s: float = 0.0
    error: str | None = None


def triage_email(
    client: anthropic.Anthropic,
    email: Email,
    *,
    model: str = DEFAULT_MODEL,
    effort: str = "low",
) -> TriageResult:
    config = MODELS[model]
    options: dict = {}
    if config.supports_effort:
        options["output_config"] = {"effort": effort}
    if config.supports_fallbacks:
        options["fallbacks"] = "default"
        options["betas"] = [FALLBACK_BETA]

    started = time.perf_counter()
    try:
        response = client.beta.messages.parse(
            model=model,
            max_tokens=16000,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": render_email(email)}],
            output_format=Triage,
            **options,
        )
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.NotFoundError):
        # Wrong key or model name: every email would fail the same way, so stop the run.
        raise
    except anthropic.APIStatusError as exc:
        return _failed(model, started, f"{exc.status_code}: {exc.message}")
    except anthropic.APIConnectionError as exc:
        return _failed(model, started, f"connection: {exc}")

    latency = time.perf_counter() - started
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read_input_tokens": response.usage.cache_read_input_tokens or 0,
        "cache_creation_input_tokens": response.usage.cache_creation_input_tokens or 0,
    }

    if response.stop_reason == "refusal":
        status: Status = "refusal"
    elif response.stop_reason == "max_tokens" or response.parsed_output is None:
        status = "truncated"
    else:
        status = "ok"

    return TriageResult(
        status=status,
        triage=response.parsed_output if status == "ok" else None,
        model_requested=model,
        model_served=response.model,
        usage=usage,
        latency_s=latency,
    )


def _failed(model: str, started: float, error: str) -> TriageResult:
    return TriageResult(
        status="error",
        triage=None,
        model_requested=model,
        latency_s=time.perf_counter() - started,
        error=error,
    )
