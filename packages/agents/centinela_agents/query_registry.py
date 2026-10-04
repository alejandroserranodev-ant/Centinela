"""
Thread-safe in-memory registry of SQL queries executed by tools.

Tools call register() when they run. The API reads with get() to serve
GET /queries/{id} for figure traceability ("Ver de dónde sale").
"""

from dataclasses import dataclass
from threading import Lock


@dataclass
class QueryRecord:
    id: str
    source: str             # view name (v_cartera_cliente) or 'alertas'
    sql: str                # SQL shown collapsed for technical users
    description: str        # Human-readable business explanation
    rows: list[dict]        # Actual data rows to display as table


_store: dict[str, QueryRecord] = {}
_lock = Lock()


def register(
    id: str,
    source: str,
    sql: str,
    description: str,
    rows: list[dict] | None = None,
) -> None:
    with _lock:
        _store[id] = QueryRecord(
            id=id, source=source, sql=sql, description=description, rows=rows or []
        )


def get(id: str) -> QueryRecord | None:
    return _store.get(id)
