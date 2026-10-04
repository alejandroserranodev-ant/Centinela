from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterator, Mapping

from centinela_tools.masking import Masking

from . import privacy
from .failures import StepTimeout, TokenCapReached
from .llm_provider import LLMProvider, LLMRequest, LLMResponse, LLMStructuredRequest, LLMStructuredResponse

RETRIED = (TimeoutError, ConnectionError, ValueError, StepTimeout)
COUNTED = ("prompt_tokens", "completion_tokens", "calls", "cached")
current: ContextVar["Meter | None"] = ContextVar("centinela_meter", default=None)


@dataclass
class Meter:
    agent: str
    spent: int
    cap: int | None
    usage: dict[str, int] = field(default_factory=lambda: dict.fromkeys(COUNTED, 0))
    attempts: int = 0
    prompts: list[dict[str, str]] = field(default_factory=list)

    def tokens(self) -> int:
        return self.spent + self.usage["prompt_tokens"] + self.usage["completion_tokens"]

    def call(self, ask: Callable[[], Any]) -> Any:
        self.attempts = 0
        while True:
            if self.cap is not None and self.tokens() >= self.cap:
                raise TokenCapReached(f"the alert spent {self.tokens()} tokens of its {self.cap}")
            self.attempts += 1
            try:
                answer = ask()
            except RETRIED:
                if self.attempts >= 2:
                    raise
                continue
            self.add(answer.usage)
            return answer

    def add(self, usage: Mapping[str, Any]) -> None:
        if usage.get("cached"):
            self.usage["cached"] += 1
            return
        self.usage["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        self.usage["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        self.usage["calls"] += 1

    def cost(self) -> dict[str, dict[str, int]]:
        return {self.agent: dict(self.usage)} if any(self.usage.values()) else {}


@contextmanager
def metering(agent: str, spent: int, cap: int | None) -> Iterator[Meter]:
    meter = Meter(agent, spent, cap)
    token = current.set(meter)
    try:
        yield meter
    finally:
        current.reset(token)


class MeteredProvider(LLMProvider):
    def __init__(self, inner: LLMProvider):
        super().__init__(inner.config)
        self.inner = inner

    def health_check(self) -> bool:
        return self.inner.health_check()

    def _call(self, ask: Callable[[], Any]) -> Any:
        meter = current.get()
        return ask() if meter is None else meter.call(ask)

    def _masked(self, request: Any) -> tuple[Masking, Any]:
        masking = privacy.current.get()
        if masking is None:
            raise privacy.Unmasked("a model call outside a masking scope would send personal data in the clear")
        masked = replace(request, system_prompt=masking.text(request.system_prompt), user_prompt=masking.text(request.user_prompt))
        meter = current.get()
        if meter is not None:
            meter.prompts.append({"agent": meter.agent, "system": masked.system_prompt, "user": masked.user_prompt})
        return masking, masked

    def generate_text(self, request: LLMRequest) -> LLMResponse:
        masking, masked = self._masked(request)
        answer = self._call(lambda: self.inner.generate_text(masked))
        return replace(answer, text=masking.unmask(answer.text))

    def generate_structured(self, request: LLMStructuredRequest) -> LLMStructuredResponse:
        masking, masked = self._masked(request)
        answer = self._call(lambda: self.inner.generate_structured(masked))
        return replace(answer, text=masking.unmask(answer.text), parsed=masking.unmask_tree(answer.parsed))


def spent(cost: Mapping[str, Mapping[str, Any]] | None) -> int:
    return sum(int(usage.get("prompt_tokens") or 0) + int(usage.get("completion_tokens") or 0) for usage in (cost or {}).values())


def add_costs(left: Mapping[str, Mapping[str, Any]] | None, right: Mapping[str, Mapping[str, Any]] | None) -> dict[str, dict[str, int]]:
    merged = {agent: dict(usage) for agent, usage in (left or {}).items()}
    for agent, usage in (right or {}).items():
        mine = merged.setdefault(agent, dict.fromkeys(COUNTED, 0))
        for key in COUNTED:
            mine[key] = int(mine.get(key) or 0) + int(usage.get(key) or 0)
    return merged
