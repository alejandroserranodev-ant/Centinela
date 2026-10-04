"""
LLM Provider abstraction: interface for pluggable language models.

Supports Ollama (local), OpenAI, and Anthropic with schema-based structured output.
The model is independent of agent logic; agents never hardcode model names.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    provider: str
    model: str
    temperature: float = 0.0
    top_p: float = 1.0
    thinking: bool = False
    timeout_seconds: int = 180


@dataclass
class LLMRequest:
    """Request to generate text from an LLM."""
    system_prompt: str
    user_prompt: str
    temperature: float | None = None
    top_p: float | None = None
    thinking: bool = False
    max_tokens: int | None = None


@dataclass
class LLMStructuredRequest:
    """Request to generate structured JSON from an LLM."""
    system_prompt: str
    user_prompt: str
    schema: dict[str, Any]
    temperature: float | None = None
    top_p: float | None = None
    thinking: bool = False
    max_tokens: int | None = None


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    text: str
    stop_reason: str
    usage: dict[str, int]
    model: str


@dataclass
class LLMStructuredResponse(LLMResponse):
    """Response from a structured LLM call."""
    parsed: dict[str, Any]


class LLMProvider(ABC):
    """
    Abstract base class for language model providers.

    Implementations must support:
    - Connecting to the model with provided configuration
    - Generating free-form text
    - Generating structured JSON with schema validation
    - Returning usage information (tokens)

    All secrets (API keys, tokens) must be read from environment only,
    never from code or stored in state.
    """

    def __init__(self, config: ModelConfig):
        """Initialize the provider with model configuration."""
        self.config = config

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check that the model is available and accessible.

        Returns True if ready, raises an exception with a clear message if not.
        """
        pass

    @abstractmethod
    def generate_text(self, request: LLMRequest) -> LLMResponse:
        """
        Generate free-form text.

        Used for non-schema steps: redacting titles, classifying rejection reasons,
        writing email bodies (with pre-masked data).

        Args:
            request: LLMRequest with system/user prompts

        Returns:
            LLMResponse with text, usage, and stop_reason

        Raises:
            TimeoutError: if request exceeds timeout
            ConnectionError: if model is unreachable
            ValueError: if model refuses output
        """
        pass

    @abstractmethod
    def generate_structured(
        self, request: LLMStructuredRequest
    ) -> LLMStructuredResponse:
        """
        Generate structured JSON matching a schema.

        Used for all agent outputs: Cause, Action, ExecutedAction, etc.
        The schema is mandatory; output must validate against it.

        Args:
            request: LLMStructuredRequest with schema

        Returns:
            LLMStructuredResponse with text, parsed dict, and usage

        Raises:
            TimeoutError: if request exceeds timeout
            ConnectionError: if model is unreachable
            ValueError: if output schema is invalid or parse fails
        """
        pass
