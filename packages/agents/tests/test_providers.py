"""
Tests for LLM provider implementations.

Run with: uv run pytest tests/test_providers.py

To test with real Ollama/OpenAI, ensure environment is configured:
  Ollama: ollama serve (default: http://localhost:11434)
  OpenAI: export OPENAI_API_KEY=sk-...
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from centinela_agents.llm_provider import LLMRequest, LLMStructuredRequest, ModelConfig
from centinela_agents.ollama_provider import OllamaProvider
from centinela_agents.openai_provider import OpenAIProvider
from centinela_agents.provider_factory import get_provider


class TestOllamaProvider:
    """Tests for Ollama provider."""

    def test_health_check_fails_without_server(self):
        """health_check raises if Ollama server is not running."""
        config = ModelConfig(provider="ollama", model="qwen3:8b")
        with patch("centinela_agents.ollama_provider.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            with pytest.raises(ValueError, match="Ollama server not reachable"):
                OllamaProvider(config)

    def test_health_check_fails_for_missing_model(self):
        """health_check raises if model is not available."""
        config = ModelConfig(provider="ollama", model="nonexistent:latest")
        with patch("centinela_agents.ollama_provider.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "models": [{"name": "qwen3:8b"}]
            }
            with pytest.raises(ValueError, match="not found in Ollama"):
                OllamaProvider(config)

    def test_generate_text_success(self):
        """generate_text returns response with usage."""
        config = ModelConfig(provider="ollama", model="qwen3:8b")
        provider = OllamaProvider.__new__(OllamaProvider)
        provider.config = config
        provider.base_url = "http://localhost:11434"
        provider.timeout = 30

        with patch("centinela_agents.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "message": {"content": "Test response"},
                "stop_reason": "stop",
                "prompt_eval_count": 10,
                "eval_count": 5,
            }

            request = LLMRequest(
                system_prompt="You are helpful.",
                user_prompt="Hello",
            )
            response = provider.generate_text(request)

            assert response.text == "Test response"
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 5
            assert response.model == "qwen3:8b"

    def test_generate_structured_success(self):
        """generate_structured parses JSON and validates."""
        config = ModelConfig(provider="ollama", model="qwen3:8b")
        provider = OllamaProvider.__new__(OllamaProvider)
        provider.config = config
        provider.base_url = "http://localhost:11434"
        provider.timeout = 30

        schema = {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "code": {"type": "integer"},
            },
            "required": ["message", "code"],
        }

        with patch("centinela_agents.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "message": {"content": '{"message": "ok", "code": 200}'},
                "stop_reason": "stop",
                "prompt_eval_count": 20,
                "eval_count": 8,
            }

            request = LLMStructuredRequest(
                system_prompt="Return JSON.",
                user_prompt="Generate response",
                schema=schema,
            )
            response = provider.generate_structured(request)

            assert response.parsed["message"] == "ok"
            assert response.parsed["code"] == 200
            assert response.usage["prompt_tokens"] == 20

    def test_generate_text_timeout(self):
        """generate_text raises TimeoutError on timeout."""
        config = ModelConfig(provider="ollama", model="qwen3:8b", timeout_seconds=1)
        provider = OllamaProvider.__new__(OllamaProvider)
        provider.config = config
        provider.base_url = "http://localhost:11434"
        provider.timeout = 1

        with patch("centinela_agents.ollama_provider.requests.post") as mock_post:
            import requests
            mock_post.side_effect = requests.Timeout()

            request = LLMRequest(
                system_prompt="You are helpful.",
                user_prompt="Hello",
            )
            with pytest.raises(TimeoutError, match="timed out"):
                provider.generate_text(request)

    def test_generate_structured_invalid_json(self):
        """generate_structured raises ValueError on invalid JSON."""
        config = ModelConfig(provider="ollama", model="qwen3:8b")
        provider = OllamaProvider.__new__(OllamaProvider)
        provider.config = config
        provider.base_url = "http://localhost:11434"
        provider.timeout = 30

        schema = {"type": "object", "properties": {"msg": {"type": "string"}}}

        with patch("centinela_agents.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "message": {"content": "Not JSON at all {invalid"},
                "stop_reason": "stop",
                "prompt_eval_count": 10,
                "eval_count": 5,
            }

            request = LLMStructuredRequest(
                system_prompt="Return JSON.",
                user_prompt="Generate",
                schema=schema,
            )
            with pytest.raises(ValueError, match="not valid JSON"):
                provider.generate_structured(request)


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    def test_init_without_api_key(self):
        """__init__ raises if OPENAI_API_KEY is not set."""
        config = ModelConfig(provider="openai", model="gpt-4o-mini")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIProvider(config)

    def test_health_check_success(self):
        """health_check returns True when API is reachable."""
        config = ModelConfig(provider="openai", model="gpt-4o-mini")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("centinela_agents.openai_provider.OpenAI") as mock_client:
                mock_client.return_value.models.list.return_value = MagicMock()
                provider = OpenAIProvider(config)
                assert provider.health_check()

    def test_generate_text_success(self):
        """generate_text returns response with usage."""
        config = ModelConfig(provider="openai", model="gpt-4o-mini")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("centinela_agents.openai_provider.OpenAI") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.models.list.return_value = MagicMock()

                provider = OpenAIProvider(config)

                mock_response = MagicMock()
                mock_response.choices = [MagicMock(
                    message=MagicMock(content="Test response"),
                    finish_reason="stop"
                )]
                mock_response.usage = MagicMock(
                    prompt_tokens=10,
                    completion_tokens=5
                )
                mock_client.chat.completions.create.return_value = mock_response

                request = LLMRequest(
                    system_prompt="You are helpful.",
                    user_prompt="Hello",
                )
                response = provider.generate_text(request)

                assert response.text == "Test response"
                assert response.usage["prompt_tokens"] == 10


class TestProviderFactory:
    """Tests for provider factory."""

    def test_get_provider_ollama(self):
        """get_provider returns OllamaProvider when provider=ollama."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "LLM_MODEL": "qwen3:8b"}):
            with patch("centinela_agents.provider_factory.OllamaProvider") as mock_ollama:
                mock_ollama.return_value = MagicMock()
                provider = get_provider()
                assert mock_ollama.called

    def test_get_provider_openai(self):
        """get_provider returns OpenAIProvider when provider=openai."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4o-mini",
            "OPENAI_API_KEY": "test-key"
        }):
            with patch("centinela_agents.provider_factory.OpenAIProvider") as mock_openai:
                mock_openai.return_value = MagicMock()
                provider = get_provider()
                assert mock_openai.called

    def test_get_provider_no_model(self):
        """get_provider raises if LLM_MODEL is not set."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            os.environ.pop("LLM_MODEL", None)
            with pytest.raises(ValueError, match="LLM_MODEL"):
                get_provider()

    def test_get_provider_unknown(self):
        """get_provider raises for unknown provider."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "unknown",
            "LLM_MODEL": "test"
        }):
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                get_provider()


def bare_ollama(**config):
    provider = OllamaProvider.__new__(OllamaProvider)
    provider.config = ModelConfig(provider="ollama", model="qwen3:8b", **config)
    provider.base_url = "http://localhost:11434"
    provider.timeout = provider.config.timeout_seconds
    return provider


OLLAMA_REPLY = {"message": {"content": '{"ok": true}'}, "done_reason": "length", "prompt_eval_count": 3, "eval_count": 2}


class TestOllamaRequestShape:
    @pytest.mark.parametrize("call", ["text", "structured"])
    def test_sampling_goes_under_options_and_thinking_as_think(self, call):
        provider = bare_ollama(temperature=0.2, top_p=0.9)
        with patch("centinela_agents.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = OLLAMA_REPLY
            if call == "text":
                provider.generate_text(LLMRequest(system_prompt="s", user_prompt="u", thinking=True, max_tokens=64))
            else:
                provider.generate_structured(LLMStructuredRequest(system_prompt="s", user_prompt="u", schema={"type": "object"}, thinking=True, max_tokens=64))
            payload = mock_post.call_args.kwargs["json"]
        assert payload["options"] == {"temperature": 0.2, "top_p": 0.9, "num_predict": 64}
        assert payload["think"] is True
        assert not {"temperature", "top_p", "thinking", "num_predict"} & payload.keys()

    def test_an_explicit_zero_temperature_is_sent_as_zero(self):
        provider = bare_ollama(temperature=0.7)
        with patch("centinela_agents.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = OLLAMA_REPLY
            provider.generate_text(LLMRequest(system_prompt="s", user_prompt="u", temperature=0.0))
            payload = mock_post.call_args.kwargs["json"]
        assert payload["options"]["temperature"] == 0.0
        assert payload["think"] is False

    @pytest.mark.parametrize("call", ["text", "structured"])
    def test_the_stop_reason_is_ollamas_done_reason(self, call):
        provider = bare_ollama()
        with patch("centinela_agents.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = OLLAMA_REPLY
            if call == "text":
                response = provider.generate_text(LLMRequest(system_prompt="s", user_prompt="u"))
            else:
                response = provider.generate_structured(LLMStructuredRequest(system_prompt="s", user_prompt="u", schema={"type": "object"}))
        assert response.stop_reason == "length"


class TestOllamaHealthCheck:
    def test_a_server_that_is_down_answers_false(self):
        provider = bare_ollama()
        with patch("centinela_agents.ollama_provider.requests.get") as mock_get:
            import requests
            mock_get.side_effect = requests.ConnectionError("refused")
            assert provider.health_check() is False

    def test_a_model_not_pulled_answers_false(self):
        provider = bare_ollama()
        with patch("centinela_agents.ollama_provider.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"models": [{"name": "llama3:8b"}]}
            assert provider.health_check() is False

    def test_a_pulled_model_answers_true(self):
        provider = bare_ollama()
        with patch("centinela_agents.ollama_provider.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"models": [{"name": "qwen3:8b"}]}
            assert provider.health_check() is True


class TestOpenAITimeout:
    def test_the_timeout_is_the_configs_and_reaches_the_client(self):
        config = ModelConfig(provider="openai", model="gpt-4o-mini", timeout_seconds=12)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("centinela_agents.openai_provider.OpenAI") as mock_client_class:
                provider = OpenAIProvider(config, skip_health_check=True)
        assert provider.timeout == 12
        assert mock_client_class.call_args.kwargs["timeout"] == 12

    def test_a_timed_out_call_raises_timeout_error_naming_the_seconds(self):
        from openai import APITimeoutError

        config = ModelConfig(provider="openai", model="gpt-4o-mini", timeout_seconds=12)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("centinela_agents.openai_provider.OpenAI") as mock_client_class:
                provider = OpenAIProvider(config, skip_health_check=True)
                mock_client_class.return_value.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())
                with pytest.raises(TimeoutError, match="after 12s"):
                    provider.generate_text(LLMRequest(system_prompt="s", user_prompt="u"))
