"""
Ollama LLM Provider: local language models via HTTP.

Ollama must be running locally (default: http://localhost:11434).
Models must support JSON schema in format parameter (qwen3+ family).
"""

import json
import os
from typing import Any

import requests

from .llm_provider import (
    LLMProvider,
    LLMRequest,
    LLMStructuredRequest,
    LLMStructuredResponse,
    LLMResponse,
    ModelConfig,
)


class OllamaProvider(LLMProvider):
    """Language model provider using local Ollama."""

    def __init__(self, config: ModelConfig):
        """
        Initialize Ollama provider.

        Args:
            config: ModelConfig with model name and optional thinking flag

        Raises:
            ValueError: if OLLAMA_BASE_URL is not set or unreachable
        """
        super().__init__(config)
        self.base_url = (
            os.getenv("OLLAMA_API_URL")
            or os.getenv("OLLAMA_BASE_URL")
            or "http://localhost:11434"
        ).rstrip("/")
        self.timeout = config.timeout_seconds

        models = self._pulled_models()
        if models is None:
            raise ValueError(
                f"Ollama server not reachable at {self.base_url}. "
                "Ensure Ollama is running: 'ollama serve' (or check OLLAMA_BASE_URL)"
            )
        if self.config.model not in models:
            raise ValueError(
                f"Model '{self.config.model}' not found in Ollama. "
                f"Available: {models}. "
                f"Pull it first: 'ollama pull {self.config.model}'"
            )

    def _pulled_models(self) -> list[str] | None:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return None
            return [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:
            return None

    def health_check(self) -> bool:
        """Check that Ollama is running and the model is available."""
        models = self._pulled_models()
        return models is not None and self.config.model in models

    def _payload(self, request: LLMRequest | LLMStructuredRequest) -> dict[str, Any]:
        options: dict[str, Any] = {
            "temperature": self.config.temperature if request.temperature is None else request.temperature,
            "top_p": self.config.top_p if request.top_p is None else request.top_p,
        }
        if request.max_tokens:
            options["num_predict"] = request.max_tokens
        return {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "think": bool(request.thinking),
            "options": options,
        }

    def _chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.Timeout as e:
            raise TimeoutError(
                f"Ollama request timed out after {self.timeout}s"
            ) from e
        except requests.RequestException as e:
            raise ConnectionError(f"Ollama connection failed: {e}") from e
        return resp.json()

    def generate_text(self, request: LLMRequest) -> LLMResponse:
        """
        Generate free-form text using Ollama.

        Args:
            request: LLMRequest with prompts

        Returns:
            LLMResponse with generated text and usage
        """
        data = self._chat(self._payload(request))
        return LLMResponse(
            text=data["message"]["content"],
            stop_reason=data.get("done_reason") or "stop",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            model=self.config.model,
        )

    def generate_structured(
        self, request: LLMStructuredRequest
    ) -> LLMStructuredResponse:
        """
        Generate structured JSON using Ollama with schema constraint.

        Ollama's `format` parameter constrains output to match a JSON schema.
        Models must support this (qwen3:8b, qwen3:14b do; qwen3:4b may not).

        Args:
            request: LLMStructuredRequest with JSON schema

        Returns:
            LLMStructuredResponse with parsed JSON and usage

        Raises:
            ValueError: if output does not match schema
        """
        payload = self._payload(request)
        payload["format"] = request.schema
        data = self._chat(payload)
        text = data["message"]["content"]

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Model output is not valid JSON: {text[:200]}"
            ) from e

        return LLMStructuredResponse(
            text=text,
            parsed=parsed,
            stop_reason=data.get("done_reason") or "stop",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            model=self.config.model,
        )
