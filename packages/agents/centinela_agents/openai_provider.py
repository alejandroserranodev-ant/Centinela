"""
OpenAI LLM Provider: remote API via OpenAI client.

Requires OPENAI_API_KEY environment variable.
Supports gpt-4o-mini, gpt-4-turbo, and other OpenAI models with JSON schema.
"""

import json
import os
from typing import Any

from .llm_provider import (
    LLMProvider,
    LLMRequest,
    LLMStructuredRequest,
    LLMStructuredResponse,
    LLMResponse,
    ModelConfig,
)

try:
    from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
except ImportError:
    raise ImportError(
        "openai package not installed. Install with: pip install openai"
    )


class OpenAIProvider(LLMProvider):
    """Language model provider using OpenAI API."""

    def __init__(self, config: ModelConfig):
        """
        Initialize OpenAI provider.

        Args:
            config: ModelConfig with model name

        Raises:
            ValueError: if OPENAI_API_KEY is not set or API is unreachable
        """
        super().__init__(config)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Set it or use a different LLM_PROVIDER."
            )

        self.client = OpenAI(api_key=api_key)

        if not self.health_check():
            raise ValueError("OpenAI API is not reachable or API key is invalid")

    def health_check(self) -> bool:
        """Check that OpenAI API is reachable."""
        try:
            # List models to verify API access
            self.client.models.list()
            return True
        except (APIError, APIConnectionError, APITimeoutError):
            return False

    def generate_text(self, request: LLMRequest) -> LLMResponse:
        """
        Generate free-form text using OpenAI API.

        Args:
            request: LLMRequest with prompts

        Returns:
            LLMResponse with generated text and usage
        """
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]

        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": request.temperature or self.config.temperature,
            "top_p": request.top_p or self.config.top_p,
        }

        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        # Note: thinking (extended thinking) requires gpt-4o or later, not all models
        if request.thinking and "4o" in self.config.model.lower():
            kwargs["thinking"] = {"type": "enabled"}

        try:
            response = self.client.chat.completions.create(**kwargs)
        except APITimeoutError as e:
            raise TimeoutError(
                f"OpenAI request timed out after {self.timeout}s"
            ) from e
        except (APIConnectionError, APIError) as e:
            raise ConnectionError(f"OpenAI API error: {e}") from e

        return LLMResponse(
            text=response.choices[0].message.content or "",
            stop_reason=response.choices[0].finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            model=self.config.model,
        )

    def generate_structured(
        self, request: LLMStructuredRequest
    ) -> LLMStructuredResponse:
        """
        Generate structured JSON using OpenAI API with JSON mode.

        OpenAI enforces JSON schema through response_format constraint
        and a system instruction. Output is guaranteed valid JSON.

        Args:
            request: LLMStructuredRequest with JSON schema

        Returns:
            LLMStructuredResponse with parsed JSON and usage

        Raises:
            ValueError: if output does not match schema (manual validation needed)
        """
        schema_str = json.dumps(request.schema)
        system_with_schema = (
            f"{request.system_prompt}\n\n"
            f"You MUST respond with valid JSON matching this schema:\n{schema_str}"
        )

        messages = [
            {"role": "system", "content": system_with_schema},
            {"role": "user", "content": request.user_prompt},
        ]

        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": request.temperature or self.config.temperature,
            "top_p": request.top_p or self.config.top_p,
            "response_format": {"type": "json_object"},  # OpenAI JSON mode
        }

        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        # Note: thinking requires gpt-4o or later
        if request.thinking and "4o" in self.config.model.lower():
            kwargs["thinking"] = {"type": "enabled"}

        try:
            response = self.client.chat.completions.create(**kwargs)
        except APITimeoutError as e:
            raise TimeoutError(
                f"OpenAI request timed out after {self.timeout}s"
            ) from e
        except (APIConnectionError, APIError) as e:
            raise ConnectionError(f"OpenAI API error: {e}") from e

        text = response.choices[0].message.content or "{}"

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Model output is not valid JSON: {text[:200]}"
            ) from e

        return LLMStructuredResponse(
            text=text,
            parsed=parsed,
            stop_reason=response.choices[0].finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            model=self.config.model,
        )
