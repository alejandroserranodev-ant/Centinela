from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Mapping, Sequence

from centinela_tools.masking import Masking

from .catalog import Catalog

MASKING = "centinela_masking"
current: ContextVar[Masking | None] = ContextVar("centinela_masking", default=None)


class Unmasked(RuntimeError):
    pass


@contextmanager
def scope(masking: Masking) -> Iterator[Masking]:
    token = current.set(masking)
    try:
        yield masking
    finally:
        current.reset(token)


def configured(masking: Masking | None) -> dict[str, Any]:
    return {"configurable": {MASKING: masking}} if masking is not None else {}


def of_config(config: Mapping[str, Any] | None) -> Masking:
    masking = ((config or {}).get("configurable") or {}).get(MASKING)
    return masking if isinstance(masking, Masking) else Masking()


def register_entity(masking: Masking, catalog: Catalog, metric: str | None, entity: Sequence[Any] | None) -> None:
    kpi = catalog.kpis.get(metric) if metric else None
    if kpi is not None and entity:
        masking.register_row(dict(zip(kpi.entity, entity)))


def register_state(masking: Masking, catalog: Catalog, state: Mapping[str, Any]) -> None:
    for key in ("detection", "alert"):
        held = state.get(key) or {}
        register_entity(masking, catalog, held.get("metric"), held.get("entity"))
    masking.register_tree(state)
