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
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = config.timeout_seconds

        if not self.health_check():
            raise ValueError(
                f"Ollama server not reachable at {self.base_url}. "
                "Ensure Ollama is running: 'ollama serve' (or check OLLAMA_BASE_URL)"
            )

    def health_check(self) -> bool:
        """Check that Ollama is running and the model is available."""
        try:
            # Check server is alive
            resp = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            if resp.status_code != 200:
                return False

            # Check model is in tags
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]

            # Model name from config (e.g., "qwen3:8b")
            if self.config.model not in models:
                raise ValueError(
                    f"Model '{self.config.model}' not found in Ollama. "
                    f"Available: {models}. "
                    f"Pull it first: 'ollama pull {self.config.model}'"
                )

            return True
        except (requests.ConnectionError, requests.Timeout, ValueError) as e:
            raise ValueError(str(e)) from e

    def generate_text(self, request: LLMRequest) -> LLMResponse:
        """
        Generate free-form text using Ollama.

        Args:
            request: LLMRequest with prompts

        Returns:
            LLMResponse with generated text and usage
        """
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "temperature": request.temperature or self.config.temperature,
            "top_p": request.top_p or self.config.top_p,
        }

        if request.thinking:
            payload["thinking"] = True

        if request.max_tokens:
            payload["num_predict"] = request.max_tokens

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

        data = resp.json()
        return LLMResponse(
            text=data["message"]["content"],
            stop_reason=data.get("stop_reason", "stop"),
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
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "temperature": request.temperature or self.config.temperature,
            "top_p": request.top_p or self.config.top_p,
            "format": request.schema,  # JSON schema constraint
        }

        if request.thinking:
            payload["thinking"] = True

        if request.max_tokens:
            payload["num_predict"] = request.max_tokens

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

        data = resp.json()
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
            stop_reason=data.get("stop_reason", "stop"),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            model=self.config.model,
        )
