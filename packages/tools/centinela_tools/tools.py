from datetime import date
from pathlib import Path

import psycopg
import yaml
from psycopg import ClientCursor, sql


def load_entries(path: Path) -> dict[str, dict]:
    return dict(yaml.safe_load(path.read_text())["metricas"])


def planner_cost(conn: psycopg.Connection, query: sql.Composable, day: date) -> float:
    with ClientCursor(conn) as cursor:
        cursor.execute(sql.SQL("EXPLAIN (FORMAT JSON) {}").format(query), {"dia": day})
        return float(cursor.fetchone()[0][0]["Plan"]["Total Cost"])
