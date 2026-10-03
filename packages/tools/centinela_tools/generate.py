import os
import re
from pathlib import Path
from typing import Any, Callable, Mapping

import psycopg
from psycopg import sql

from .compiler import compile_kpi, function_definition
from .language import check_card
from .paths import GENERATED, METRICAS, SQL_DIR
from .refusal import Refused
from .settings import Settings
from .sources import Sources, load_sources
from .tools import load_entries, planner_cost

BANNER = (
    "-- Written by `uv run python -m centinela_tools.generate` in packages/tools, from data/kernel/fuentes.yaml,\n"
    "-- data/metricas.yaml and the views of data/sql/03_capa_semantica.sql and data/sql/04_vistas_causa.sql.\n"
    "-- Never edit it by hand: the defect is in those sources. Applied after 04_vistas_causa.sql.\n"
)
ROLES = """DO $roles$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'centinela_lector') THEN
    CREATE ROLE centinela_lector LOGIN PASSWORD 'centinela_lector';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'centinela_kernel') THEN
    CREATE ROLE centinela_kernel LOGIN PASSWORD 'centinela_kernel';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'centinela_propietario') THEN
    CREATE ROLE centinela_propietario NOLOGIN;
  END IF;
  EXECUTE format('REVOKE TEMPORARY ON DATABASE %I FROM PUBLIC', current_database());
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO centinela_lector, centinela_kernel', current_database());
END
$roles$;
ALTER ROLE centinela_lector SET default_transaction_read_only = on;
ALTER ROLE centinela_kernel SET default_transaction_read_only = on;
REVOKE EXECUTE ON FUNCTION lo_create(oid), lo_creat(integer), lo_from_bytea(oid, bytea), lo_put(oid, bigint, bytea) FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA centinela TO centinela_lector, centinela_kernel, centinela_propietario;
"""
FECHA_CORTE = """ALTER FUNCTION centinela.fecha_corte() SECURITY DEFINER SET search_path = centinela, pg_temp;
ALTER FUNCTION centinela.fecha_corte() OWNER TO centinela_propietario;
"""


def view_names(sql_dir: Path) -> list[str]:
    names = []
    for name in ("03_capa_semantica.sql", "04_vistas_causa.sql"):
        names += re.findall(r"CREATE OR REPLACE VIEW (v_[a-z_]+)", (sql_dir / name).read_text())
    return names


def render(sources: Sources, entries: Mapping[str, Mapping[str, Any]], views: list[str], cost: Callable[[sql.Composable], float], settings: Settings) -> str:
    parts = [BANNER, ROLES]
    for name, table in sources.tables.items():
        grant = sql.SQL("GRANT SELECT ({}) ON {} TO centinela_kernel, centinela_propietario;\n").format(
            sql.SQL(", ").join(sql.Identifier(column) for column in table.columns), sql.Identifier("centinela", name)
        )
        parts.append(grant.as_string())
    parts.append(FECHA_CORTE)
    for view in views:
        parts.append(sql.SQL("GRANT SELECT ON {} TO centinela_lector;\n").format(sql.Identifier("centinela", view)).as_string())
    for metric, entry in entries.items():
        if "kernel" not in entry:
            continue
        check_card(entry)
        estimated = cost(compile_kpi(entry["kernel"], sources).query)
        if estimated > settings.max_cost:
            raise Refused("costo", f"{metric}: the planner estimates {estimated:.0f}, over the cap of {settings.max_cost:.0f}")
        parts.append(function_definition(metric, entry["kernel"], sources).as_string())
    return "".join(parts)


def database_cost(dsn: str) -> Callable[[sql.Composable], float]:
    conn = psycopg.connect(dsn, autocommit=True)
    day = conn.execute("SELECT centinela.fecha_corte()").fetchone()[0]
    return lambda query: planner_cost(conn, query, day)


def refuse_cost(query: sql.Composable) -> float:
    raise RuntimeError("a metric carries kernel:, so CENTINELA_DSN must name a database loaded with data/sql/01 to 04")


def main() -> None:
    entries = load_entries(METRICAS)
    needs_database = any("kernel" in entry for entry in entries.values())
    cost = database_cost(os.environ["CENTINELA_DSN"]) if needs_database and "CENTINELA_DSN" in os.environ else refuse_cost
    GENERATED.write_text(render(load_sources(), entries, view_names(SQL_DIR), cost, Settings.from_env()))


if __name__ == "__main__":
    main()
