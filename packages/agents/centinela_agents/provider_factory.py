"""
Factory for LLM provider selection based on environment configuration.

Environment variables:
  LLM_PROVIDER: "ollama" | "openai" | "anthropic" (default: "ollama")
  LLM_MODEL: model name (e.g., "qwen3:8b", "gpt-4o-mini")
  OLLAMA_API_URL: Ollama HTTP endpoint (default: http://localhost:11434)
  OLLAMA_BASE_URL: legacy alias of OLLAMA_API_URL (used if OLLAMA_API_URL is unset)
  OPENAI_API_KEY: OpenAI API key (required if provider=openai)
  ANTHROPIC_API_KEY: Anthropic API key (required if provider=anthropic)
"""

import os
from typing import Literal

from .llm_provider import LLMProvider, ModelConfig
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider


def get_provider(
    provider_name: str | None = None,
    model_name: str | None = None,
    thinking: bool = False,
) -> LLMProvider:
    """
    Get an LLM provider based on environment or explicit parameters.

    Args:
        provider_name: Override LLM_PROVIDER env var (ollama|openai|anthropic)
        model_name: Override LLM_MODEL env var
        thinking: Enable extended thinking (if provider supports it)

    Returns:
        Configured LLMProvider instance

    Raises:
        ValueError: if provider is unknown or configuration is invalid
    """
    provider = (provider_name or os.getenv("LLM_PROVIDER", "ollama")).lower()
    model = model_name or os.getenv("LLM_MODEL", "")

    if not model:
        raise ValueError(
            "LLM_MODEL environment variable not set. "
            "Set it to a model name (e.g., 'qwen3:8b' for Ollama, 'gpt-4o-mini' for OpenAI)"
        )

    config = ModelConfig(
        provider=provider,
        model=model,
        thinking=thinking,
    )

    if provider == "ollama":
        return OllamaProvider(config)
    elif provider == "openai":
        return OpenAIProvider(config)
    elif provider == "anthropic":
        raise NotImplementedError("Anthropic provider not yet implemented")
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Choose one of: ollama, openai, anthropic"
        )


def get_reasoning_provider() -> LLMProvider | None:
    """
    The provider of the steps that reason (Analista, Estratega), when LLM_MODEL_RAZONA names a model.

    Returns None when it is unset or empty, and those steps use the provider of every other step.
    """
    model = os.getenv("LLM_MODEL_RAZONA", "").strip()
    return get_provider(model_name=model, thinking=True) if model else None
