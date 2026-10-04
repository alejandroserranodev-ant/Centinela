"""
An in-process cache of model answers, keyed by everything a request sends.

A leaf asks at temperature 0, so the same prompt, schema and model answer the same: a day run
again, an eval repeated, or an alert reopened after a rejection pays once. Only temperature 0 is
cached, because a sampled answer is meant to differ. A hit returns the stored answer with zero
tokens and `cached` set, so a cost count never charges it twice. Nothing is written to disk or to
a database, because no agent writes anywhere.
"""

import hashlib
import json
from collections import OrderedDict
from dataclasses import asdict, replace
from typing import Any

from .llm_provider import LLMProvider, LLMRequest, LLMResponse, LLMStructuredRequest, LLMStructuredResponse

HIT_USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "cached": 1}


def request_key(model: str, kind: str, request: LLMRequest | LLMStructuredRequest) -> str:
    payload = json.dumps({"model": model, "kind": kind, **asdict(request)}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class CachingProvider(LLMProvider):
    def __init__(self, inner: LLMProvider, size: int):
        super().__init__(inner.config)
        self.inner = inner
        self.size = size
        self.answers: OrderedDict[str, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def health_check(self) -> bool:
        return self.inner.health_check()

    def _answer(self, kind: str, request: LLMRequest | LLMStructuredRequest, call):
        temperature = self.config.temperature if request.temperature is None else request.temperature
        if temperature != 0:
            return call(request)
        key = request_key(self.config.model, kind, request)
        if key in self.answers:
            self.answers.move_to_end(key)
            self.hits += 1
            return replace(self.answers[key], usage=dict(HIT_USAGE))
        answer = call(request)
        self.misses += 1
        self.answers[key] = answer
        if len(self.answers) > self.size:
            self.answers.popitem(last=False)
        return answer

    def generate_text(self, request: LLMRequest) -> LLMResponse:
        return self._answer("text", request, self.inner.generate_text)

    def generate_structured(self, request: LLMStructuredRequest) -> LLMStructuredResponse:
        return self._answer("structured", request, self.inner.generate_structured)
