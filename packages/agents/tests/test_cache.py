# The answer cache: a repeated request at temperature 0 pays once, and a hit is charged no tokens.
import os
from unittest.mock import MagicMock, patch

from centinela_agents.cache import CachingProvider
from centinela_agents.llm_provider import LLMRequest, LLMResponse, LLMStructuredRequest, LLMStructuredResponse, ModelConfig
from centinela_agents.provider_factory import get_provider


def inner():
    provider = MagicMock()
    provider.config = ModelConfig(provider="openai", model="gpt-4o-mini")
    provider.generate_text.side_effect = lambda request: LLMResponse(text=request.user_prompt, stop_reason="stop", usage={"prompt_tokens": 10, "completion_tokens": 2}, model="m")
    provider.generate_structured.side_effect = lambda request: LLMStructuredResponse(text="{}", parsed={"ok": request.user_prompt}, stop_reason="stop", usage={"prompt_tokens": 10, "completion_tokens": 2}, model="m")
    return provider


def text(prompt, temperature=0.0):
    return LLMRequest(system_prompt="s", user_prompt=prompt, temperature=temperature)


def test_a_repeated_request_calls_the_model_once_and_the_hit_costs_no_tokens():
    model = inner()
    cache = CachingProvider(model, 8)

    first = cache.generate_text(text("a"))
    second = cache.generate_text(text("a"))

    assert model.generate_text.call_count == 1
    assert second.text == first.text
    assert first.usage["prompt_tokens"] == 10
    assert second.usage == {"prompt_tokens": 0, "completion_tokens": 0, "cached": 1}
    assert (cache.hits, cache.misses) == (1, 1)


def test_a_sampled_request_is_never_cached():
    model = inner()
    cache = CachingProvider(model, 8)

    cache.generate_text(text("a", 0.7))
    cache.generate_text(text("a", 0.7))

    assert model.generate_text.call_count == 2


def test_another_schema_is_another_answer():
    model = inner()
    cache = CachingProvider(model, 8)

    cache.generate_structured(LLMStructuredRequest(system_prompt="s", user_prompt="a", schema={"type": "object"}, temperature=0.0))
    cache.generate_structured(LLMStructuredRequest(system_prompt="s", user_prompt="a", schema={"type": "array"}, temperature=0.0))

    assert model.generate_structured.call_count == 2


def test_the_oldest_answer_leaves_first():
    model = inner()
    cache = CachingProvider(model, 1)

    cache.generate_text(text("a"))
    cache.generate_text(text("b"))
    cache.generate_text(text("a"))

    assert model.generate_text.call_count == 3


def test_the_factory_wraps_unless_the_size_is_zero():
    with patch("centinela_agents.provider_factory.OllamaProvider") as ollama:
        ollama.return_value = inner()
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "LLM_MODEL": "m", "CENTINELA_CACHE_RESPUESTAS": "4"}):
            assert isinstance(get_provider(), CachingProvider)
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "LLM_MODEL": "m", "CENTINELA_CACHE_RESPUESTAS": "0"}):
            assert not isinstance(get_provider(), CachingProvider)
