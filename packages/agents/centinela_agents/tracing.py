import os
from typing import Any, Mapping, Protocol


class Tracer(Protocol):
    def config(self, session: str) -> Mapping[str, Any]: ...


class HandlerTracer:
    def __init__(self, handler: Any):
        self.handler = handler

    def config(self, session: str) -> Mapping[str, Any]:
        return {"callbacks": [self.handler], "metadata": {"langfuse_session_id": session}}


def langfuse_tracer(env: Mapping[str, str] = os.environ) -> HandlerTracer | None:
    if not (env.get("LANGFUSE_PUBLIC_KEY") and env.get("LANGFUSE_SECRET_KEY")):
        return None
    from langfuse.langchain import CallbackHandler

    return HandlerTracer(CallbackHandler())
