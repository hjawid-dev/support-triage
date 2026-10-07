from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    # List prices in USD per million tokens, checked September 2026.
    input_per_mtok: float
    output_per_mtok: float
    cache_read_per_mtok: float
    supports_effort: bool
    supports_fallbacks: bool


MODELS = {
    "claude-opus-5-5": ModelConfig(4.00, 20.00, 0.20, supports_effort=True, supports_fallbacks=True),
    "claude-sonnet-5-5": ModelConfig(2.00, 10.00, 0.20, supports_effort=True, supports_fallbacks=True),
    "claude-haiku-4-5": ModelConfig(1.00, 5.00, 0.10, supports_effort=False, supports_fallbacks=False),
}

DEFAULT_MODEL = "claude-opus-5-5"

# Writing to the prompt cache costs 1.25 times the normal input price.
CACHE_WRITE_MULTIPLIER = 1.25


def resolve(model: str) -> str | None:
    """Name in MODELS for a model id, or None when it is not one of them.

    The API can answer with a dated snapshot id such as claude-haiku-4-5-20251001.
    """
    if model in MODELS:
        return model
    return next((name for name in MODELS if model.startswith(f"{name}-")), None)


def cost_usd(model: str, usage: dict) -> float | None:
    """Cost of one request from the token counts the API reported. None for an unknown model."""
    name = resolve(model)
    if name is None:
        return None
    config = MODELS[name]
    return (
        usage.get("input_tokens", 0) * config.input_per_mtok
        + usage.get("output_tokens", 0) * config.output_per_mtok
        + usage.get("cache_read_input_tokens", 0) * config.cache_read_per_mtok
        + usage.get("cache_creation_input_tokens", 0) * config.input_per_mtok * CACHE_WRITE_MULTIPLIER
    ) / 1_000_000
