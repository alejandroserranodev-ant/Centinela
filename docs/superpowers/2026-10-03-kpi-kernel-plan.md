# KPI kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the KPI kernel. It has a closed definition language owned by `data`, a compiler to `psycopg.sql` composition, guards on cost, time and cardinality, two database roles that cannot write, a generator of `data/sql/05_kpis.generated.sql`, and four read-only tools served over MCP. The plan builds no current metric, which is spec 5's work.

**Architecture:** A new Python package, `packages/tools/centinela_tools/`, reads two files in `data/kernel/`: `lenguaje.schema.json`, the language as JSON Schema, and `fuentes.yaml`, which says what the kernel may read. It compiles a `kernel:` block to a `Composed` that takes `dia`, and refuses with a named guard anything it cannot bound. A generator writes the roles, their column grants and one `SECURITY DEFINER` function per base metric. The tools run compiled SQL inside a read-only transaction under `statement_timeout`. An approved KPI runs as stored text after its hash is checked. A FastMCP server exposes the four tools over stdio. Static tests run with no database. Tests marked `db` run against a disposable Postgres loaded with `data/sql/01` to `04`.

**Tech Stack:** Python ≥ 3.12, uv, psycopg ≥ 3.2 (`Composable.as_string()` with no context), jsonschema ≥ 4.23 (Draft 2020-12), PyYAML, `mcp` (FastMCP), pytest. PostgreSQL 16 in Docker for the `db` tests.

**Spec:** `docs/superpowers/2026-10-03-kpi-kernel.md`. Read it whole, with the section "Amendments made while planning" that Task 1 adds. It depends on spec 1, `2026-10-03-normative-foundations.md`: read its "The laws (level L0)". Spec 5, `2026-10-03-current-kpis-in-kernel-pending-5.md`, is not planned here. It rebuilds the current metrics and adds the primitives they need.

## Global Constraints

- Code is English. The words the data and the spec name keep their Spanish: the YAML and JSON keys exactly as the spec writes them (`fuente`, `unir`, `abierto_al_dia`, `ventana`, `filtro`, `agrupar`, `medida`, `razon`, `linea_base`, `salida`, `fuga`), the tool names (`kpi_validar`, `kpi_dry_run`, `kpi_consultar`, `kpi_catalogo`), the guard names, and the ISO 22400-2 fields (`unidad`, `rango`, `tendencia`, `temporalidad`, `audiencia`).
- The guards are a closed list, `refusal.GUARDS = ("lenguaje", "fuente", "reloj", "costo", "tiempo", "cardinalidad", "hash", "catalogo")`. Every refusal raises `Refused(guard, detail)`, and the detail is English.
- **No fragment of SQL is built from a string at runtime.** Every `sql.SQL(...)` in `centinela_tools/` takes one string constant. Identifiers come only from `fuentes.yaml` through `sql.Identifier`, and values only through `sql.Literal` or `sql.Placeholder`. The one exception is the stored text of an approved KPI, which runs only after its hash matches.
- **No role a tool holds can write.** `centinela_lector` holds `SELECT` on the `v_*` views and `EXECUTE` on `centinela.k_*`. `centinela_kernel` holds `SELECT` on the readable columns of `fuentes.yaml`, column by column. Neither holds `TEMPORARY`, `CREATE`, `INSERT`, `UPDATE`, `DELETE` or `TRUNCATE`.
- **Hand-written source carries no comments**, except one header of at most ten lines on a script or a test. MCP tool descriptions go in `@server.tool(description=...)`, never in docstrings.
- `data/csv/` and `data/sql/01` to `04` are not touched. `data/sql/05_kpis.generated.sql` is never edited by hand. It is written by `uv run python -m centinela_tools.generate` and committed.
- The `db` tests never use the volume of `data/docker-compose.yml`. They use the disposable container `centinela-kernel-test` on port 55432 (Task 5).
- Documentation is English, present tense, and states each fact on one page. **No permanent page cites a spec or a plan.** No literal count of anything that grows. Prose cites code as `path/to/file.py:member(parameters)`.
- Commit messages are short sentences that carry the reason. They are written through `git commit -q -F - <<'MSG'` and end with the `Co-Authored-By:` and `Claude-Session:` lines of the session. **No commit is made without asking the user first.** Nothing merges to `main`.
- A link inside text this plan quotes for another page is written `](<path>)`, relative to that page, so the link check of `CLAUDE.md` skips it here. Drop the angle brackets when pasting.
- Python commands run from `packages/tools/` with `uv`. If `uv` is not on `PATH`, it is `~/.local/bin/uv`. A test that fails is fixed in the code, never by loosening its assertion.

## Decisions taken while planning

Task 1 writes each into the spec's section "Amendments made while planning", and Task 8 writes it onto the page that owns it.

1. **Scope: infrastructure only** (decided with the user). This plan builds the language, `fuentes.yaml`, the compiler, the guards, the roles, the generator, the four tools and the server, and tests them with fixture blocks in `packages/tools/tests/fixtures/metricas.yaml`. No entry of `data/metricas.yaml` gains a `kernel:` block. As the spec's table is written, almost none could: `saldo_vencido` needs conditional sums, `variacion_costo_pct` and `veces_intervalo_habitual` need lag, `dias_retraso` needs `CASE`, and `descuento_en_exceso` compares one column with another. Spec 5 adds each primitive with its bound. The `DOUBTS.md` debt stays filed, and Task 8 updates it to say that `kpi_catalogo` exists and serves no base metric yet.
2. **Each date column has a role** (decided with the user). "Applies `dia` to every date column" breaks `fecha_vencimiento` and `fecha_esperada`, which are future by nature. `fuentes.yaml` gives each date column one role:
   - `evento`: the row exists from that day, so the compiler adds `<= dia`.
   - `plazo`: a promised date, read as is.
   - `cierre`: an event that closes the row, such as `fecha_recibida`. The compiler reads it as `CASE WHEN c <= dia THEN c END`.

   `ventana`, `linea_base` and `abierto_al_dia.desde` take only an `evento` date. `agrupar ... por` takes an `evento` or a `plazo` date.
3. **Only many-to-one joins** (decided with the user). A join must reach the whole primary key of its target, along a `REFERENCES` of `01_esquema.sql`, or onto the PK of a `ref_*` table (`ref_topes_descuento` by `segmento`, `ref_margen_minimo_linea` by `linea`), which have no FK. Joins are `LEFT JOIN`, so a null FK (`clientes.vendedor_id`) never drops a row. A child table, such as `pagos` of an invoice, reaches a KPI only as a **closing** (`cierres:` of the source), and only inside `abierto_al_dia.hasta`. It compiles to `NOT EXISTS (... fecha_pago <= dia)`, which is the spec's "a payment joins only when `fecha_pago <= dia`". The data holds at most one full payment per invoice (`pagos.csv` has one per invoice with `valor = valor_total`), so "open" means "no payment up to `dia`".
4. **A source with no date of its own names the join that dates it.** `pedidos_detalle` declares `fechada_por: pedidos`, and a KPI over it without `unir: [pedidos]` is refused by `reloj`. The bound of that join goes in `WHERE`, so its `LEFT JOIN` behaves as an inner one.
5. **`pedidos.estado` is `fuga` except for values known when the row is created** (decided with the user). The generator decides `Cancelado` when it creates the order (`generar_dataset.py`, 4% at random, never invoiced), and only `Pendiente de despacho` holds the end of the dataset. `fuga: {estado: {razon, conocidos_al_crear: [Cancelado]}}` admits `=`, `!=` or `en` on those values in a `filtro` and nothing else. `ordenes_compra.estado` has no known value, so no filter reads it. Without this, spec 5's parity with `v_ventas` breaks on every sales metric.
6. **The base functions belong to `centinela_kernel`** (decided with the user), `SECURITY DEFINER` with `SET search_path = pg_catalog, pg_temp` and fully qualified names, so a base KPI reads only the readable columns too. The setup superuser creates them and changes their owner with `ALTER FUNCTION ... OWNER TO`, which needs no `CREATE` for the kernel role. `EXECUTE` is revoked from `PUBLIC` and granted to `centinela_lector`.
7. **The read-only user is `centinela_lector`.** `data/AGENTS.md` named no role, and none existed. Both roles are `LOGIN`, with the password equal to the name, the same posture as the compose's `centinela/centinela` for the local dataset. They are created in an idempotent `DO` block.
8. **`fecha_corte()` becomes `SECURITY DEFINER`, owned by `centinela_kernel`**, in `05`. A view's function runs with the caller's privileges, so `centinela_lector` reading `v_cartera_cliente` would fail on `inventario_diario`. The kit file `03` is not touched.
9. **`05_kpis.generated.sql` holds the roles, the grants and the functions**, one file written by one command from `fuentes.yaml`, `metricas.yaml` and the view names of `03` and `04`. The function needs the role and its grants first, and the spec names one setup step. A test compares the committed file with what the generator writes.
10. **The entity of a KPI is its `agrupar`** (one to three items). `salida` names only `valor`, plus `base` and `delta` with a `linea_base`. One row per entity then holds by construction. `dia` and `periodo` are reserved names.
11. **One time frame per KPI**: at most one of `ventana`, `abierto_al_dia` and `linea_base`. With none, the compiler bounds every event date by `<= dia`. `linea_base` measures the **last complete period** before `dia`: for a week, the Monday `s` with `s + 6 <= dia`; for a month, the one whose last day is `<= dia`. It compares that period against the mean of the N before it.
12. **Language bounds the spec leaves open**: an `en` list of at most 20 literals; no `%` in a text literal, because psycopg would read it as a placeholder in an approved KPI's stored text; a literal of the column's type; text of at most 200 characters.
13. **ISO 22400-2 fields**: `unidad` (text), `rango` (`{min, max}`, each a number or `null`), `tendencia` (`mayor_es_mejor` or `menor_es_mejor`), `temporalidad` (`diaria`, `semanal` or `mensual`), and `audiencia` (one or more of `operacion`, `supervision`, `gerencia`). They are required only on an entry that carries `kernel:`. They are defined in `$defs/ficha` of the same schema.
14. **`kpi_validar` takes `dia`**, because `EXPLAIN` with a null day folds the plan to nothing. The generator explains each base KPI on `centinela.fecha_corte()`, and needs `CENTINELA_DSN` only when an entry carries `kernel:`.
15. **The tools receive a block, never SQL.** `kpi_dry_run` compiles the block it receives. `kpi_consultar` receives an id. The approved KPIs reach the server as a JSON file named by `CENTINELA_KPIS_APROBADOS`, which the orchestrator writes for the run. That is code, as the spec asks. The server speaks stdio. How an agent reaches it stays undecided in `packages/agents`.
16. **Guard settings by environment variable**, with defaults sized in Task 6: `CENTINELA_KERNEL_COSTO_MAX`, `CENTINELA_KERNEL_TIMEOUT_MS`, `CENTINELA_KERNEL_GRUPOS_MAX` and `CENTINELA_KERNEL_MUESTRA`.
17. **The `db` tests run against a disposable container** (decided with the user), started by the command in Task 5 and named by `CENTINELA_TEST_DSN`. Without it they are skipped, and the skip says why. A person still checks the compose's initdb and pgAdmin, which the tests do not cover.

## Review Focus

1. **`centinela_lector` reads a view that calls `fecha_corte()`.** Without decision 8, `SELECT * FROM v_cartera_cliente` fails with permission denied on `inventario_diario`. Expected: rows. Task 5 pins it with `test_the_reader_reads_a_view_that_calls_fecha_corte`.
2. **A literal carries a quote, a semicolon or a `%`.** Expected: a quote or a semicolon runs as a harmless literal and no table changes. `%` is refused by `lenguaje`. Task 3 pins `%` with `test_a_bound_of_the_language_is_refused[percent]`. Task 6 pins the injection with `test_a_literal_with_sql_in_it_stays_a_literal`.
3. **A weekly baseline on a mid-week day.** Expected: the measured week is the last complete one, never the current one. Task 6 pins it with `test_a_weekly_baseline_measures_the_last_complete_week` on Saturday 2026-02-28 and Sunday 2026-03-01.
4. **A day before the dataset, or an entity with no earlier period.** Expected: no row and no exception. Task 6 pins it with `test_a_day_before_the_dataset_returns_no_rows`.
5. **An approved KPI whose stored text writes.** Even with a matching hash, `DELETE FROM centinela.pedidos` fails in the read-only transaction with no grant, and the row count does not change. Task 6 pins it with `test_an_approved_kpi_that_writes_fails_and_changes_nothing`.

## File structure

| Path | Responsibility | Task |
|---|---|---|
| `data/kernel/fuentes.yaml` | what the kernel may read | 2 |
| `data/kernel/lenguaje.schema.json` | the language and the ISO 22400-2 fields | 3 |
| `packages/tools/pyproject.toml`, `packages/tools/uv.lock` | the package and its pinned dependencies | 2 |
| `packages/tools/centinela_tools/__init__.py` | empty | 2 |
| `packages/tools/centinela_tools/paths.py` | the paths into `data/` | 2 |
| `packages/tools/centinela_tools/refusal.py` | `Refused` and the closed list of guards | 2 |
| `packages/tools/centinela_tools/sources.py` | loads and checks `fuentes.yaml` | 2 |
| `packages/tools/centinela_tools/language.py` | validates a block and a card against the schema | 3 |
| `packages/tools/centinela_tools/compiler.py` | block → `Compiled`, the function definition, the hash | 4 |
| `packages/tools/centinela_tools/settings.py` | the guards' settings | 5 |
| `packages/tools/centinela_tools/tools.py` | the catalogue and the four tools | 5, 6 |
| `packages/tools/centinela_tools/generate.py` | writes `05_kpis.generated.sql` | 5 |
| `packages/tools/centinela_tools/server.py` | the MCP server | 7 |
| `packages/tools/tests/support.py` | the parser of `01_esquema.sql`, the fixture blocks | 2, 4 |
| `packages/tools/tests/conftest.py` | the `db` fixtures | 5 |
| `packages/tools/tests/fixtures/metricas.yaml` | three fixture KPIs | 4 |
| `packages/tools/tests/test_*.py` | one file per module, plus `test_roles.py` and `test_tools_db.py` | 2 to 7 |
| `data/sql/05_kpis.generated.sql` | generated | 5 |
| `data/docker-compose.yml` | mounts `05` | 5 |
| the pages | Tasks 8 and 9 | 8, 9 |

---

### Task 1: Rename the spec now that its plan exists, and write the amendments into it

**Files:**
- Rename: `docs/superpowers/2026-10-03-kpi-kernel-pending-4.md` → `docs/superpowers/2026-10-03-kpi-kernel.md`
- Create: `docs/superpowers/2026-10-03-kpi-kernel-plan.md` (this plan)

**Interfaces:**
- Consumes: none.
- Produces: the spec at the path this plan's header names, with the section "Amendments made while planning".

- [ ] **Step 1: Find every citation of the old path**

Run: `grep -rn "kpi-kernel-pending-4" --include='*.md' . | grep -v node_modules`
Expected: only lines of this plan. Any other hit is a file to update in Step 4.

- [ ] **Step 2: Rename**

Run: `git mv docs/superpowers/2026-10-03-kpi-kernel-pending-4.md docs/superpowers/2026-10-03-kpi-kernel.md`

- [ ] **Step 3: Update the status line**

Replace `**Status:** pending its plan. **Depends on:**` with
`**Status:** planned in `2026-10-03-kpi-kernel-plan.md`. **Depends on:**`

- [ ] **Step 4: Append the amendments**

At the end of the spec, add `## Amendments made while planning`, opening with "Each item supersedes the line of this spec it names; the plan builds the amended version." Then add one bullet per item 1 to 16 of this plan's "Decisions taken while planning", each with its reason. Shorten the wording, but keep every value: role names, guard names, bounds and environment variables. Also delete the parenthesis `(at ... until Task 1 renames it)` from this plan's `**Spec:**` line.

- [ ] **Step 5: Verify**

Run: `git status --short`
Expected: `R` from the old path to the new one, `M` on it, and `?? docs/superpowers/2026-10-03-kpi-kernel-plan.md`. Nothing else.

- [ ] **Step 6: Ask the user, then commit**

```bash
git add docs/superpowers/
git commit -q -F - <<'MSG'
Plan the KPI kernel and rename its spec, with the amendments the real schema forced written into it

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 2: The package, `fuentes.yaml`, and its check against the schema

**Files:**
- Create: `packages/tools/pyproject.toml`, `packages/tools/centinela_tools/{__init__,paths,refusal,sources}.py`, `data/kernel/fuentes.yaml`, `packages/tools/tests/support.py`, `packages/tools/tests/test_sources.py`
- Generated: `packages/tools/uv.lock`
- Modify: `GENERATED.md`, the row for `uv sync` and `uv lock`

**Interfaces:**
- Produces:
  - `paths.ROOT`, `paths.DATA`, `paths.FUENTES`, `paths.LENGUAJE`, `paths.METRICAS`, `paths.SQL_DIR`, `paths.GENERATED`, each a `Path`
  - `refusal.GUARDS: tuple[str, ...]` and `refusal.Refused(guard: str, detail: str)`, an `Exception` with `.guard` and `.detail`. A guard outside `GUARDS` raises `ValueError`.
  - `sources.Table(name, key, columns, dates, leaks, excluded)`, `sources.Join(name, origin, table, on)`, `sources.Closing(name, table, on, date)`, `sources.Source(name, joins, closings, dimensions, dated_by)` and `sources.Sources(tables, sources)`, all frozen dataclasses
  - `sources.load_sources(path: Path = FUENTES) -> Sources`, which raises `ValueError("fuentes.yaml: ...")` on an inconsistent file
  - `tests/support.py:schema_tables(path) -> dict[str, SchemaTable]`, where `SchemaTable(columns: dict[str, str], key: tuple[str, ...], references: dict[str, str])`

- [ ] **Step 1: Write `pyproject.toml` and sync**

```toml
[project]
name = "centinela-tools"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "jsonschema>=4.23",
  "mcp>=1.10",
  "psycopg[binary]>=3.2",
  "pyyaml>=6.0",
]

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["centinela_tools"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["db: needs CENTINELA_TEST_DSN, a scratch PostgreSQL loaded with data/sql/01 to 04"]
```

Create `centinela_tools/__init__.py` empty. Run: `uv sync`
Then run: `uv run python -c "from psycopg import sql; print(sql.SQL('{} = {}').format(sql.Identifier('a','b'), sql.Literal('x')).as_string())"`
Expected: `"a"."b" = 'x'`. If `as_string()` requires a context, the installed psycopg is older than 3.2: stop and pin `psycopg[binary]>=3.2.3`.

- [ ] **Step 2: Write `paths.py` and `refusal.py`**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
FUENTES = DATA / "kernel" / "fuentes.yaml"
LENGUAJE = DATA / "kernel" / "lenguaje.schema.json"
METRICAS = DATA / "metricas.yaml"
SQL_DIR = DATA / "sql"
GENERATED = SQL_DIR / "05_kpis.generated.sql"
```

```python
GUARDS = ("lenguaje", "fuente", "reloj", "costo", "tiempo", "cardinalidad", "hash", "catalogo")


class Refused(Exception):
    def __init__(self, guard: str, detail: str):
        if guard not in GUARDS:
            raise ValueError(f"{guard} is not a guard of the kernel")
        super().__init__(f"{guard}: {detail}")
        self.guard = guard
        self.detail = detail
```

- [ ] **Step 3: Write the parser of the schema and the failing tests**

`packages/tools/tests/support.py`:

```python
# Helpers the kernel's tests share: a parser of data/sql/01_esquema.sql, so fuentes.yaml is checked
# against the tables the schema really creates, and the fixture KPIs of tests/fixtures/metricas.yaml.
import copy
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from centinela_tools.paths import SQL_DIR

TESTS = Path(__file__).resolve().parent
FIXTURE_METRICAS = TESTS / "fixtures" / "metricas.yaml"
TABLE = re.compile(r"CREATE TABLE (\w+) \((.*?)\);", re.S)
SQL_TYPES = {"varchar": "text", "char": "text", "text": "text", "int": "integer", "bigint": "bigint", "numeric": "numeric", "date": "date"}


@dataclass(frozen=True)
class SchemaTable:
    columns: dict[str, str]
    key: tuple[str, ...]
    references: dict[str, str]


def split_top(body: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in body:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    return [*parts, current.strip()]


def schema_tables(path: Path = SQL_DIR / "01_esquema.sql") -> dict[str, SchemaTable]:
    tables = {}
    for name, body in TABLE.findall(path.read_text()):
        columns, key, references = {}, (), {}
        for part in split_top(body):
            words = part.split()
            if words[0] == "PRIMARY":
                key = tuple(column.strip() for column in part[part.index("(") + 1 : part.rindex(")")].split(","))
                continue
            columns[words[0]] = SQL_TYPES[re.match(r"[a-z]+", words[1]).group(0)]
            if "PRIMARY KEY" in part:
                key = (words[0],)
            if "REFERENCES" in words:
                references[words[0]] = words[words.index("REFERENCES") + 1]
        tables[name] = SchemaTable(columns, key, references)
    return tables


def fixture_entries() -> dict:
    return copy.deepcopy(yaml.safe_load(FIXTURE_METRICAS.read_text())["metricas"])


def fixture_block(metric: str) -> dict:
    return fixture_entries()[metric]["kernel"]
```

`packages/tools/tests/test_sources.py`:

```python
# fuentes.yaml is checked against data/sql/01_esquema.sql, so it cannot name a table, a column, a
# key or a join the schema does not hold, and every column of the schema is either readable or
# excluded with a reason. A planted inconsistency per rule of sources.py:load_sources fails the load.
import copy

import pytest
import yaml

from centinela_tools.paths import FUENTES
from centinela_tools.sources import load_sources

from support import schema_tables

SCHEMA = schema_tables()
SOURCES = load_sources()


def test_every_table_and_column_exists_in_the_schema_with_its_type():
    for name, table in SOURCES.tables.items():
        assert name in SCHEMA, name
        for column, kind in table.columns.items():
            assert SCHEMA[name].columns.get(column) == kind, f"{name}.{column}"


def test_every_column_of_the_schema_is_readable_or_excluded_with_a_reason():
    for name, table in SOURCES.tables.items():
        assert set(table.columns) | set(table.excluded) == set(SCHEMA[name].columns), name
        assert all(reason.strip() for reason in table.excluded.values()), name


def test_every_key_is_the_primary_key_of_the_schema():
    for name, table in SOURCES.tables.items():
        assert set(table.key) == set(SCHEMA[name].key), name


def test_every_join_follows_a_foreign_key_or_reaches_a_ref_tables_key():
    for source in SOURCES.sources.values():
        owners = {source.name: source.name, **{join.name: join.table for join in source.joins.values()}}
        for join in source.joins.values():
            origin = owners[join.origin]
            for local in join.on:
                assert SCHEMA[origin].references.get(local) == join.table or join.table.startswith("ref_"), f"{source.name}.{join.name}"


def test_every_closing_reads_a_child_that_references_its_source():
    for source in SOURCES.sources.values():
        for closing in source.closings.values():
            for child_column in closing.on:
                assert SCHEMA[closing.table].references.get(child_column) == source.name, f"{source.name}.{closing.name}"


def test_a_persons_name_is_excluded_and_the_two_states_are_fuga():
    assert "nombre" in SOURCES.tables["vendedores"].excluded
    assert SOURCES.tables["pedidos"].leaks["estado"] == ("Cancelado",)
    assert SOURCES.tables["ordenes_compra"].leaks["estado"] == ()


def test_every_date_column_has_a_role():
    for name, table in SOURCES.tables.items():
        assert set(table.dates) == {c for c, kind in table.columns.items() if kind == "date"}, name


def planted(change, tmp_path):
    data = copy.deepcopy(yaml.safe_load(FUENTES.read_text()))
    change(data)
    path = tmp_path / "fuentes.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True))
    return path


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda d: d["tablas"]["facturas"]["fechas"].pop("fecha_vencimiento"), id="a-date-without-role"),
        pytest.param(lambda d: d["tablas"]["facturas"]["fechas"].update(fecha_factura="hoy"), id="a-role-outside-the-list"),
        pytest.param(lambda d: d["fuentes"]["pagos"]["uniones"]["facturas"].update(por={"factura_id": "cliente_id"}), id="a-join-short-of-the-key"),
        pytest.param(lambda d: d["fuentes"]["pagos"]["uniones"]["clientes"].update(desde="nadie"), id="a-join-from-nowhere"),
        pytest.param(lambda d: d["fuentes"]["pedidos_detalle"].pop("fechada_por"), id="a-source-with-no-date"),
        pytest.param(lambda d: d["fuentes"]["pedidos"]["dimensiones"].append("pedidos.estado"), id="a-fuga-dimension"),
        pytest.param(lambda d: d["fuentes"]["facturas"]["cierres"]["pagada"].update(fecha="valor"), id="a-closing-without-event"),
    ],
)
def test_an_inconsistent_fuentes_fails_the_load(change, tmp_path):
    with pytest.raises(ValueError, match="fuentes.yaml"):
        load_sources(planted(change, tmp_path))
```

- [ ] **Step 4: Run them to verify they fail**

Run: `uv run pytest tests/test_sources.py -q`
Expected: collection fails with `ModuleNotFoundError: No module named 'centinela_tools.sources'`.

- [ ] **Step 5: Write `data/kernel/fuentes.yaml`**

```yaml
version: 1
tablas:
  vendedores:
    clave: [vendedor_id]
    columnas: { vendedor_id: text, region: text }
    excluidas: { nombre: "el nombre de una persona; ante un agente un vendedor es su vendedor_id" }
  clientes:
    clave: [cliente_id]
    columnas: { cliente_id: text, nombre: text, segmento: text, ciudad: text, region: text, vendedor_id: text, plazo_dias: integer, cupo_credito: bigint, fecha_alta: date }
    fechas: { fecha_alta: evento }
  proveedores:
    clave: [proveedor_id]
    columnas: { proveedor_id: text, nombre: text, lead_time_dias: integer, pais: text }
  productos:
    clave: [sku]
    columnas: { sku: text, nombre: text, linea: text, proveedor_id: text, clase_abc: text, unidad: text }
  bodegas:
    clave: [bodega_id]
    columnas: { bodega_id: text, nombre: text, ciudad: text }
  lista_precios:
    clave: [sku, fecha_vigencia]
    columnas: { sku: text, fecha_vigencia: date, precio_lista: numeric }
    fechas: { fecha_vigencia: evento }
  costos_proveedor:
    clave: [sku, fecha_vigencia]
    columnas: { sku: text, proveedor_id: text, fecha_vigencia: date, costo_unitario: numeric }
    fechas: { fecha_vigencia: evento }
  ordenes_compra:
    clave: [oc_id]
    columnas: { oc_id: text, proveedor_id: text, sku: text, bodega_id: text, fecha_oc: date, fecha_esperada: date, fecha_recibida: date, cantidad: integer, costo_unitario: numeric, estado: text }
    fechas: { fecha_oc: evento, fecha_esperada: plazo, fecha_recibida: cierre }
    fuga:
      estado: { razon: "guarda cómo terminó la orden al final del dataset, no su estado en el día simulado", conocidos_al_crear: [] }
  pedidos:
    clave: [pedido_id]
    columnas: { pedido_id: text, fecha: date, cliente_id: text, vendedor_id: text, ciudad: text, canal: text, estado: text }
    fechas: { fecha: evento }
    fuga:
      estado: { razon: "Pendiente de despacho es el estado al final del dataset; Cancelado se decide al crear el pedido", conocidos_al_crear: [Cancelado] }
  pedidos_detalle:
    clave: [pedido_id, linea_n]
    columnas: { pedido_id: text, linea_n: integer, sku: text, cantidad: integer, precio_lista: numeric, precio_unitario: numeric, descuento_pct: numeric, aprobacion_especial: text, valor_neto: numeric, costo_unitario: numeric }
  facturas:
    clave: [factura_id]
    columnas: { factura_id: text, pedido_id: text, cliente_id: text, fecha_factura: date, fecha_vencimiento: date, valor_neto: numeric, iva: numeric, valor_total: numeric }
    fechas: { fecha_factura: evento, fecha_vencimiento: plazo }
  pagos:
    clave: [pago_id]
    columnas: { pago_id: text, factura_id: text, fecha_pago: date, valor: numeric, medio_pago: text }
    fechas: { fecha_pago: evento }
  inventario_diario:
    clave: [fecha, bodega_id, sku]
    columnas: { fecha: date, bodega_id: text, sku: text, existencia_inicial: integer, entradas: integer, salidas: integer, existencia_final: integer }
    fechas: { fecha: evento }
  ref_topes_descuento:
    clave: [segmento]
    columnas: { segmento: text, tope_descuento_pct: numeric }
  ref_margen_minimo_linea:
    clave: [linea]
    columnas: { linea: text, margen_minimo_pct: numeric }
fuentes:
  pedidos_detalle:
    fechada_por: pedidos
    uniones:
      pedidos: { desde: pedidos_detalle, tabla: pedidos, por: { pedido_id: pedido_id } }
      productos: { desde: pedidos_detalle, tabla: productos, por: { sku: sku } }
      clientes: { desde: pedidos, tabla: clientes, por: { cliente_id: cliente_id } }
      vendedores: { desde: pedidos, tabla: vendedores, por: { vendedor_id: vendedor_id } }
      topes: { desde: clientes, tabla: ref_topes_descuento, por: { segmento: segmento } }
      margen_minimo: { desde: productos, tabla: ref_margen_minimo_linea, por: { linea: linea } }
    dimensiones: [pedidos_detalle.pedido_id, pedidos_detalle.linea_n, pedidos_detalle.sku, pedidos.cliente_id, pedidos.vendedor_id, pedidos.canal, pedidos.ciudad, productos.linea, productos.clase_abc, clientes.segmento, clientes.region, vendedores.region]
  pedidos:
    uniones:
      clientes: { desde: pedidos, tabla: clientes, por: { cliente_id: cliente_id } }
      vendedores: { desde: pedidos, tabla: vendedores, por: { vendedor_id: vendedor_id } }
    dimensiones: [pedidos.cliente_id, pedidos.vendedor_id, pedidos.canal, pedidos.ciudad, clientes.segmento, clientes.region]
  facturas:
    uniones:
      clientes: { desde: facturas, tabla: clientes, por: { cliente_id: cliente_id } }
    cierres:
      pagada: { tabla: pagos, por: { factura_id: factura_id }, fecha: fecha_pago }
    dimensiones: [facturas.factura_id, facturas.cliente_id, clientes.segmento, clientes.region, clientes.vendedor_id]
  pagos:
    uniones:
      facturas: { desde: pagos, tabla: facturas, por: { factura_id: factura_id } }
      clientes: { desde: facturas, tabla: clientes, por: { cliente_id: cliente_id } }
    dimensiones: [facturas.cliente_id, pagos.medio_pago, clientes.segmento]
  ordenes_compra:
    uniones:
      proveedores: { desde: ordenes_compra, tabla: proveedores, por: { proveedor_id: proveedor_id } }
      productos: { desde: ordenes_compra, tabla: productos, por: { sku: sku } }
    dimensiones: [ordenes_compra.oc_id, ordenes_compra.proveedor_id, ordenes_compra.sku, ordenes_compra.bodega_id, productos.linea, productos.clase_abc]
  inventario_diario:
    uniones:
      productos: { desde: inventario_diario, tabla: productos, por: { sku: sku } }
    dimensiones: [inventario_diario.sku, inventario_diario.bodega_id, productos.linea, productos.clase_abc]
  costos_proveedor:
    uniones:
      productos: { desde: costos_proveedor, tabla: productos, por: { sku: sku } }
      proveedores: { desde: costos_proveedor, tabla: proveedores, por: { proveedor_id: proveedor_id } }
    dimensiones: [costos_proveedor.sku, costos_proveedor.proveedor_id, productos.linea, productos.clase_abc]
  lista_precios:
    uniones:
      productos: { desde: lista_precios, tabla: productos, por: { sku: sku } }
    dimensiones: [lista_precios.sku, productos.linea, productos.clase_abc]
```

The `cierres` mapping is `{column of the child: column of the source}`.

- [ ] **Step 6: Write `sources.py`**

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .paths import FUENTES

ROLES = frozenset({"evento", "plazo", "cierre"})
TYPES = frozenset({"text", "integer", "bigint", "numeric", "date", "boolean"})


@dataclass(frozen=True)
class Table:
    name: str
    key: tuple[str, ...]
    columns: Mapping[str, str]
    dates: Mapping[str, str]
    leaks: Mapping[str, tuple[Any, ...]]
    excluded: Mapping[str, str]


@dataclass(frozen=True)
class Join:
    name: str
    origin: str
    table: str
    on: Mapping[str, str]


@dataclass(frozen=True)
class Closing:
    name: str
    table: str
    on: Mapping[str, str]
    date: str


@dataclass(frozen=True)
class Source:
    name: str
    joins: Mapping[str, Join]
    closings: Mapping[str, Closing]
    dimensions: frozenset[str]
    dated_by: str | None


@dataclass(frozen=True)
class Sources:
    tables: Mapping[str, Table]
    sources: Mapping[str, Source]


def load_sources(path: Path = FUENTES) -> Sources:
    data = yaml.safe_load(path.read_text())
    tables = {name: table_of(name, spec) for name, spec in data["tablas"].items()}
    return Sources(tables, {name: source_of(name, spec, tables) for name, spec in data["fuentes"].items()})


def problem(message: str) -> ValueError:
    return ValueError(f"fuentes.yaml: {message}")


def table_of(name: str, spec: Mapping[str, Any]) -> Table:
    columns = dict(spec["columnas"])
    dates = dict(spec.get("fechas", {}))
    leaks = spec.get("fuga", {})
    excluded = dict(spec.get("excluidas", {}))
    if set(columns.values()) - TYPES:
        raise problem(f"{name} declares a type outside {sorted(TYPES)}")
    if {column for column, kind in columns.items() if kind == "date"} != set(dates):
        raise problem(f"{name}: every date column, and only a date column, carries a role")
    if set(dates.values()) - ROLES:
        raise problem(f"{name}: a date role is one of {sorted(ROLES)}")
    if set(leaks) - set(columns) or any(not leak.get("razon") for leak in leaks.values()):
        raise problem(f"{name}: a fuga column is readable and carries its razon")
    if set(excluded) & set(columns) or set(spec["clave"]) - set(columns):
        raise problem(f"{name}: an excluded column is not readable, and the key is readable")
    known = {column: tuple(leak.get("conocidos_al_crear", [])) for column, leak in leaks.items()}
    return Table(name, tuple(spec["clave"]), columns, dates, known, excluded)


def source_of(name: str, spec: Mapping[str, Any], tables: Mapping[str, Table]) -> Source:
    if name not in tables:
        raise problem(f"the source {name} is no table")
    owners = {name: tables[name]}
    joins = {}
    for join_name, join in spec.get("uniones", {}).items():
        remote = tables.get(join["tabla"])
        origin = owners.get(join["desde"])
        if join_name in owners or origin is None:
            raise problem(f"{name}: {join_name} reuses a name or joins from {join['desde']}, declared after it or nowhere")
        if remote is None or set(join["por"].values()) != set(remote.key) or set(join["por"]) - set(origin.columns):
            raise problem(f"{name}: {join_name} joins columns of {join['desde']} to the whole key of {join['tabla']}")
        owners[join_name] = remote
        joins[join_name] = Join(join_name, join["desde"], join["tabla"], dict(join["por"]))
    closings = {}
    for closing_name, closing in spec.get("cierres", {}).items():
        child = tables.get(closing["tabla"])
        if closing_name in owners or child is None or child.dates.get(closing["fecha"]) != "evento":
            raise problem(f"{name}: the closing {closing_name} reads an event date of a declared table")
        if set(closing["por"]) - set(child.columns) or set(closing["por"].values()) - set(tables[name].columns):
            raise problem(f"{name}: the closing {closing_name} matches columns both tables hold")
        closings[closing_name] = Closing(closing_name, closing["tabla"], dict(closing["por"]), closing["fecha"])
    dated_by = spec.get("fechada_por")
    if dated_by is not None and dated_by not in joins:
        raise problem(f"{name}: fechada_por names {dated_by}, which is no join of it")
    if "evento" not in owners[dated_by or name].dates.values():
        raise problem(f"{name} has no event date, and no fechada_por names a join that has one")
    dimensions = frozenset(spec.get("dimensiones", []))
    for ref in dimensions:
        alias, _, column = ref.partition(".")
        table = owners.get(alias)
        if table is None or column not in table.columns or column in table.leaks:
            raise problem(f"{name}: the dimension {ref} is no readable column of the source or its joins")
    return Source(name, joins, closings, dimensions, dated_by)
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_sources.py -q`
Expected: all pass. If a schema test fails, the defect is in `fuentes.yaml`, never in the test.

- [ ] **Step 8: Add `packages/tools` to the uv row of `GENERATED.md`**

Change the row's first two cells to `` `uv sync` and `uv lock`, run in `packages/agents` and in `packages/tools` `` and `` `packages/agents/uv.lock` and `packages/tools/uv.lock`, each from the `pyproject.toml` beside it ``. Keep the third cell, with `pyproject.toml` in the plural.

- [ ] **Step 9: Ask the user, then commit**

```bash
git add packages/tools data/kernel/fuentes.yaml GENERATED.md
git commit -q -F - <<'MSG'
Declare what the kernel may read in fuentes.yaml, checked against the schema so it cannot name what the tables do not hold

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 3: The language as a JSON Schema, with one refusal per bound

**Files:**
- Create: `data/kernel/lenguaje.schema.json`, `packages/tools/centinela_tools/language.py`, `packages/tools/tests/fixtures/metricas.yaml`, `packages/tools/tests/test_language.py`

**Interfaces:**
- Consumes: `refusal.Refused`, `paths.LENGUAJE`, `support.fixture_block(metric)`
- Produces: `language.check_block(block: Mapping) -> None` and `language.check_card(entry: Mapping) -> None`. Both raise `Refused("lenguaje", "<path>: <message>")`. The path is `kernel` for the block's root and `ficha` for the card's root.

- [ ] **Step 1: Write the fixture KPIs**

`packages/tools/tests/fixtures/metricas.yaml`:

```yaml
metricas:
  oc_abiertas:
    descripcion: Órdenes de compra abiertas por proveedor en el día simulado
    unidad: órdenes
    rango: { min: 0, max: null }
    tendencia: menor_es_mejor
    temporalidad: diaria
    audiencia: [operacion]
    kernel:
      fuente: ordenes_compra
      abierto_al_dia: { desde: ordenes_compra.fecha_oc, hasta: ordenes_compra.fecha_recibida }
      agrupar: [ordenes_compra.proveedor_id]
      medida: { agregado: count }
      salida: { valor: ordenes_abiertas }
  facturas_abiertas:
    descripcion: Valor de las facturas sin pago en el día simulado, por cliente
    unidad: COP
    rango: { min: 0, max: null }
    tendencia: menor_es_mejor
    temporalidad: diaria
    audiencia: [supervision, gerencia]
    fuente_umbral: "fixture de prueba; no cita una política"
    kernel:
      fuente: facturas
      abierto_al_dia: { desde: facturas.fecha_factura, hasta: pagada }
      agrupar: [facturas.cliente_id]
      medida: { agregado: sum, de: facturas.valor_total }
      salida: { valor: saldo_abierto }
  ventas_semana_linea:
    descripcion: Ventas netas de la última semana completa por línea, frente a las 8 anteriores
    unidad: COP
    rango: { min: 0, max: null }
    tendencia: mayor_es_mejor
    temporalidad: semanal
    audiencia: [gerencia]
    kernel:
      fuente: pedidos_detalle
      unir: [pedidos, productos]
      filtro:
        - { columna: pedidos.estado, op: "!=", valor: Cancelado }
      agrupar: [productos.linea]
      medida: { agregado: sum, de: pedidos_detalle.valor_neto }
      linea_base: { columna: pedidos.fecha, periodo: semana, n: 8, salida: delta_pct }
      salida: { valor: ventas, base: ventas_base, delta: ventas_delta_pct }
```

- [ ] **Step 2: Write the failing tests**

`packages/tools/tests/test_language.py`:

```python
# One planted violation per bound of the language table in data/kernel/lenguaje.schema.json. Each
# must be refused by the guard lenguaje, with the detail naming the key that broke the bound.
import pytest

from centinela_tools.language import check_block, check_card
from centinela_tools.refusal import Refused

from support import fixture_block, fixture_entries

COL = "pedidos_detalle.valor_neto"


def weekly():
    return fixture_block("ventas_semana_linea")


def with_(change):
    block = weekly()
    change(block)
    return block


def op(left, right):
    return {"op": "+", "izq": left, "der": right}


@pytest.mark.parametrize("metric", ["oc_abiertas", "facturas_abiertas", "ventas_semana_linea"])
def test_every_fixture_block_and_card_is_in_the_language(metric):
    check_block(fixture_block(metric))
    check_card(fixture_entries()[metric])


@pytest.mark.parametrize(
    "block, path",
    [
        pytest.param(with_(lambda b: b.update(unir=["pedidos", "productos", "clientes", "topes"])), "unir", id="four-joins"),
        pytest.param(with_(lambda b: (b.pop("linea_base"), b["salida"].pop("base"), b["salida"].pop("delta"), b.update(ventana={"columna": "pedidos.fecha", "dias": 366}))), "ventana/dias", id="window-past-365"),
        pytest.param(with_(lambda b: b.update(filtro=[{"columna": "pedidos_detalle.cantidad", "op": ">", "valor": i} for i in range(6)])), "filtro", id="six-filters"),
        pytest.param(with_(lambda b: b.update(agrupar=["productos.linea", "productos.clase_abc", "pedidos.canal", "pedidos.ciudad"])), "agrupar", id="four-groups"),
        pytest.param(with_(lambda b: b.update(medida={"agregado": "sum", "de": op(op(op(COL, COL), COL), COL)})), "medida/de", id="expression-depth-three"),
        pytest.param(with_(lambda b: (b.pop("medida"), b.update(razon={"numerador": {"razon": {}}, "denominador": {"agregado": "count"}}))), "razon/numerador", id="ratio-of-a-ratio"),
        pytest.param(with_(lambda b: b["linea_base"].update(n=13)), "linea_base/n", id="baseline-past-12"),
        pytest.param(with_(lambda b: b["salida"].pop("valor")), "salida", id="no-output-value"),
        pytest.param(with_(lambda b: b.update(color="rojo")), "kernel", id="unknown-key"),
        pytest.param(with_(lambda b: b.update(razon={"numerador": {"agregado": "count"}, "denominador": {"agregado": "count"}})), "kernel", id="measure-and-ratio"),
        pytest.param(with_(lambda b: b.update(ventana={"columna": "pedidos.fecha", "dias": 7})), "kernel", id="two-time-frames"),
        pytest.param(with_(lambda b: b["filtro"][0].update(op="like")), "filtro/0/op", id="operator-outside-the-list"),
        pytest.param(with_(lambda b: b["medida"].update(agregado="stddev")), "medida/agregado", id="aggregate-outside-the-list"),
        pytest.param(with_(lambda b: b["filtro"][0].update(valor="50%")), "filtro/0/valor", id="percent"),
        pytest.param(with_(lambda b: b["filtro"][0].update(op="en", valor=[str(i) for i in range(21)])), "filtro/0/valor", id="list-past-20"),
        pytest.param(with_(lambda b: b["salida"].pop("base")), "salida", id="baseline-without-base"),
    ],
)
def test_a_bound_of_the_language_is_refused(block, path):
    with pytest.raises(Refused) as refused:
        check_block(block)
    assert refused.value.guard == "lenguaje"
    assert refused.value.detail.startswith(path), refused.value.detail


def test_an_unknown_key_is_named():
    with pytest.raises(Refused, match="color"):
        check_block(with_(lambda b: b.update(color="rojo")))


def test_a_card_without_tendencia_is_refused():
    entry = fixture_entries()["oc_abiertas"]
    entry.pop("tendencia")
    with pytest.raises(Refused, match="tendencia") as refused:
        check_card(entry)
    assert refused.value.guard == "lenguaje"
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_language.py -q`
Expected: `ModuleNotFoundError: No module named 'centinela_tools.language'`.

- [ ] **Step 4: Write `data/kernel/lenguaje.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "kernel",
  "type": "object",
  "additionalProperties": false,
  "required": ["fuente", "agrupar", "salida"],
  "properties": {
    "fuente": { "$ref": "#/$defs/nombre" },
    "unir": { "type": "array", "maxItems": 3, "uniqueItems": true, "items": { "$ref": "#/$defs/nombre" } },
    "abierto_al_dia": {
      "type": "object", "additionalProperties": false, "required": ["desde", "hasta"],
      "properties": {
        "desde": { "$ref": "#/$defs/columna" },
        "hasta": { "anyOf": [{ "$ref": "#/$defs/columna" }, { "$ref": "#/$defs/nombre" }] }
      }
    },
    "ventana": {
      "type": "object", "additionalProperties": false, "required": ["columna", "dias"],
      "properties": { "columna": { "$ref": "#/$defs/columna" }, "dias": { "type": "integer", "minimum": 1, "maximum": 365 } }
    },
    "filtro": { "type": "array", "maxItems": 5, "items": { "$ref": "#/$defs/filtro" } },
    "agrupar": {
      "type": "array", "minItems": 1, "maxItems": 3,
      "items": { "anyOf": [{ "$ref": "#/$defs/columna" }, { "$ref": "#/$defs/periodo" }] }
    },
    "medida": { "$ref": "#/$defs/medida" },
    "razon": {
      "type": "object", "additionalProperties": false, "required": ["numerador", "denominador"],
      "properties": { "numerador": { "$ref": "#/$defs/medida" }, "denominador": { "$ref": "#/$defs/medida" } }
    },
    "linea_base": {
      "type": "object", "additionalProperties": false, "required": ["columna", "periodo", "n", "salida"],
      "properties": {
        "columna": { "$ref": "#/$defs/columna" },
        "periodo": { "enum": ["semana", "mes"] },
        "n": { "type": "integer", "minimum": 1, "maximum": 12 },
        "salida": { "enum": ["delta", "delta_pct"] }
      }
    },
    "salida": {
      "type": "object", "additionalProperties": false, "required": ["valor"],
      "properties": { "valor": { "$ref": "#/$defs/nombre" }, "base": { "$ref": "#/$defs/nombre" }, "delta": { "$ref": "#/$defs/nombre" } }
    }
  },
  "oneOf": [{ "required": ["medida"] }, { "required": ["razon"] }],
  "not": {
    "anyOf": [
      { "required": ["ventana", "abierto_al_dia"] },
      { "required": ["ventana", "linea_base"] },
      { "required": ["abierto_al_dia", "linea_base"] }
    ]
  },
  "if": { "required": ["linea_base"] },
  "then": { "properties": { "salida": { "required": ["valor", "base", "delta"] } } },
  "else": { "properties": { "salida": { "properties": { "base": false, "delta": false } } } },
  "$defs": {
    "nombre": { "type": "string", "pattern": "^[a-z][a-z0-9_]{0,62}$" },
    "columna": { "type": "string", "pattern": "^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$" },
    "periodo": {
      "type": "object", "additionalProperties": false, "required": ["columna", "por"],
      "properties": { "columna": { "$ref": "#/$defs/columna" }, "por": { "enum": ["semana", "mes"] } }
    },
    "literal": {
      "anyOf": [
        { "type": "string", "maxLength": 200, "pattern": "^[^%]*$" },
        { "type": "number" },
        { "type": "boolean" }
      ]
    },
    "filtro": {
      "type": "object", "additionalProperties": false, "required": ["columna", "op", "valor"],
      "properties": {
        "columna": { "$ref": "#/$defs/columna" },
        "op": { "enum": ["=", "!=", "<", "<=", ">", ">=", "en"] },
        "valor": true
      },
      "if": { "properties": { "op": { "const": "en" } } },
      "then": { "properties": { "valor": { "type": "array", "minItems": 1, "maxItems": 20, "items": { "$ref": "#/$defs/literal" } } } },
      "else": { "properties": { "valor": { "$ref": "#/$defs/literal" } } }
    },
    "operacion": {
      "type": "object", "additionalProperties": false, "required": ["op", "izq", "der"],
      "properties": { "op": { "enum": ["+", "-", "*", "/"] }, "izq": { "$ref": "#/$defs/columna" }, "der": { "$ref": "#/$defs/columna" } }
    },
    "expresion": {
      "anyOf": [
        { "$ref": "#/$defs/columna" },
        { "$ref": "#/$defs/operacion" },
        {
          "type": "object", "additionalProperties": false, "required": ["op", "izq", "der"],
          "properties": {
            "op": { "enum": ["+", "-", "*", "/"] },
            "izq": { "anyOf": [{ "$ref": "#/$defs/columna" }, { "$ref": "#/$defs/operacion" }] },
            "der": { "anyOf": [{ "$ref": "#/$defs/columna" }, { "$ref": "#/$defs/operacion" }] }
          }
        }
      ]
    },
    "medida": {
      "type": "object", "additionalProperties": false, "required": ["agregado"],
      "properties": {
        "agregado": { "enum": ["sum", "avg", "count", "min", "max", "mediana"] },
        "de": { "$ref": "#/$defs/expresion" }
      },
      "if": { "properties": { "agregado": { "not": { "const": "count" } } } },
      "then": { "required": ["de"] }
    },
    "ficha": {
      "type": "object",
      "required": ["descripcion", "unidad", "rango", "tendencia", "temporalidad", "audiencia"],
      "properties": {
        "descripcion": { "type": "string", "minLength": 1 },
        "unidad": { "type": "string", "minLength": 1 },
        "rango": {
          "type": "object", "additionalProperties": false, "required": ["min", "max"],
          "properties": { "min": { "type": ["number", "null"] }, "max": { "type": ["number", "null"] } }
        },
        "tendencia": { "enum": ["mayor_es_mejor", "menor_es_mejor"] },
        "temporalidad": { "enum": ["diaria", "semanal", "mensual"] },
        "audiencia": { "type": "array", "minItems": 1, "uniqueItems": true, "items": { "enum": ["operacion", "supervision", "gerencia"] } }
      }
    }
  }
}
```

- [ ] **Step 5: Write `language.py`**

```python
import json
from functools import cache
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from .paths import LENGUAJE
from .refusal import Refused


@cache
def validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    schema = json.loads(LENGUAJE.read_text())
    card = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/ficha"}
    return Draft202012Validator(schema), Draft202012Validator(card)


def refuse_first(validator: Draft202012Validator, document: Mapping[str, Any], root: str) -> None:
    error = best_match(validator.iter_errors(document))
    if error is not None:
        path = "/".join(str(step) for step in error.absolute_path) or root
        raise Refused("lenguaje", f"{path}: {error.message}")


def check_block(block: Mapping[str, Any]) -> None:
    refuse_first(validators()[0], block, "kernel")


def check_card(entry: Mapping[str, Any]) -> None:
    refuse_first(validators()[1], entry, "ficha")
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_language.py -q`
Expected: all pass. If `best_match` reports a deeper path for an `anyOf`, the `startswith` assertion still holds, because the deeper path begins with the key. If it reports a sibling key instead, fix the schema, never the expected path.

- [ ] **Step 7: Ask the user, then commit**

```bash
git add data/kernel/lenguaje.schema.json packages/tools
git commit -q -F - <<'MSG'
Write the kernel's language as a JSON Schema in data, so a block outside its keys or bounds is refused before any SQL exists

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 4: The compiler, with the clock applied by construction

**Files:**
- Create: `packages/tools/centinela_tools/compiler.py`, `packages/tools/tests/test_compiler.py`

**Interfaces:**
- Consumes: `language.check_block`, `sources.Sources`, `refusal.Refused`, `support.fixture_block`
- Produces:
  - `compiler.COMPILER_VERSION = "1"`
  - `compiler.Compiled(query: sql.Composable, columns: tuple[tuple[str, str], ...], entity: tuple[str, ...])`
  - `compiler.compile_kpi(block, sources, day: sql.Composable = sql.Placeholder("dia")) -> Compiled`
  - `compiler.function_definition(metric: str, block, sources) -> sql.Composable`
  - `compiler.Frozen(sql: str, hash: str, compiler_version: str)`, `compiler.freeze(compiled) -> Frozen`, `compiler.digest(text: str) -> str` (sha256 hex)

- [ ] **Step 1: Write the failing tests**

`packages/tools/tests/test_compiler.py`:

```python
# The compiler with no database: every refusal of the guards fuente, reloj and lenguaje that needs
# fuentes.yaml, the clock written into the SQL by construction, and two checks over the package's
# source: every SQL fragment is a constant, and no query is built from a formatted string.
import ast
from pathlib import Path

import pytest
from psycopg import sql

import centinela_tools
from centinela_tools.compiler import compile_kpi, digest, freeze, function_definition
from centinela_tools.refusal import Refused
from centinela_tools.sources import load_sources

from support import fixture_block

SOURCES = load_sources()
PACKAGE = Path(centinela_tools.__file__).parent


def text(block):
    return compile_kpi(block, SOURCES).query.as_string()


def refused(block):
    with pytest.raises(Refused) as caught:
        compile_kpi(block, SOURCES)
    return caught.value


def changed(metric, change):
    block = fixture_block(metric)
    change(block)
    return block


@pytest.mark.parametrize("metric", ["oc_abiertas", "facturas_abiertas", "ventas_semana_linea"])
def test_every_fixture_compiles_to_a_composition(metric):
    compiled = compile_kpi(fixture_block(metric), SOURCES)
    assert isinstance(compiled.query, sql.Composable)
    assert compiled.entity == tuple(name for name, _ in compiled.columns[: len(compiled.entity)])


def test_the_entity_is_agrupar_and_the_columns_carry_types():
    compiled = compile_kpi(fixture_block("ventas_semana_linea"), SOURCES)
    assert compiled.entity == ("linea",)
    assert compiled.columns == (("linea", "text"), ("ventas", "numeric"), ("ventas_base", "numeric"), ("ventas_delta_pct", "numeric"))


def test_an_open_row_reads_a_closing_date_only_up_to_dia():
    assert '("ordenes_compra"."fecha_recibida" IS NULL OR "ordenes_compra"."fecha_recibida" > CAST(%(dia)s AS date))' in text(fixture_block("oc_abiertas"))


def test_a_payment_closes_an_invoice_only_up_to_dia():
    expected = 'NOT EXISTS (SELECT 1 FROM "centinela"."pagos" AS "pagada" WHERE "pagada"."factura_id" = "facturas"."factura_id" AND "pagada"."fecha_pago" <= CAST(%(dia)s AS date))'
    assert expected in text(fixture_block("facturas_abiertas"))


def test_every_event_date_reached_is_bounded_by_dia():
    query = text(fixture_block("ventas_semana_linea"))
    assert '"pedidos"."fecha" <= CAST(%(dia)s AS date)' in query
    assert '"facturas"."fecha_factura" <= CAST(%(dia)s AS date)' in text(fixture_block("facturas_abiertas"))


def test_a_weekly_baseline_uses_only_complete_weeks():
    query = text(fixture_block("ventas_semana_linea"))
    assert "date_trunc('week', CAST(%(dia)s AS date) - 6)::date" in query
    assert '"pedidos"."fecha" < (' in query


def test_every_join_is_a_left_join():
    query = text(fixture_block("ventas_semana_linea"))
    assert query.count("LEFT JOIN") == 2 and " JOIN " not in query.replace("LEFT JOIN", "").replace("JOIN periodos", "")


def test_a_closing_date_in_a_measure_is_read_as_empty_after_dia():
    block = changed("oc_abiertas", lambda b: b.update(medida={"agregado": "max", "de": "ordenes_compra.fecha_recibida"}))
    assert 'CASE WHEN "ordenes_compra"."fecha_recibida" <= CAST(%(dia)s AS date) THEN "ordenes_compra"."fecha_recibida" END' in text(block)


@pytest.mark.parametrize(
    "block, guard, words",
    [
        pytest.param(changed("oc_abiertas", lambda b: b.update(fuente="clientes")), "fuente", "not a source", id="unknown-source"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(unir=["bodegas"])), "fuente", "not a join", id="undeclared-join"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(unir=["clientes", "pedidos"])), "fuente", "before it", id="join-out-of-order"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(unir=["pedidos", "vendedores"], agrupar=["vendedores.nombre"])), "fuente", "not readable", id="a-persons-name"),
        pytest.param(changed("ventas_semana_linea", lambda b: b["filtro"][0].update(op="=", valor="Pendiente de despacho")), "fuente", "end of the dataset", id="fuga-unknown-value"),
        pytest.param(changed("ventas_semana_linea", lambda b: b["filtro"][0].update(op="<")), "fuente", "end of the dataset", id="fuga-ordering"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(medida={"agregado": "max", "de": "pedidos.estado"})), "fuente", "end of the dataset", id="fuga-in-a-measure"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(agrupar=["pedidos_detalle.cantidad"])), "fuente", "not a dimension", id="undeclared-dimension"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(unir=["productos"])), "reloj", "dates it", id="undated-source"),
        pytest.param(changed("facturas_abiertas", lambda b: (b.pop("abierto_al_dia"), b.update(ventana={"columna": "facturas.fecha_vencimiento", "dias": 30}))), "reloj", "not a date of an event", id="window-on-a-term"),
        pytest.param(changed("facturas_abiertas", lambda b: b["abierto_al_dia"].update(hasta="facturas.fecha_vencimiento")), "reloj", "closes a row", id="open-until-a-term"),
        pytest.param(changed("facturas_abiertas", lambda b: b["abierto_al_dia"].update(hasta="cobrada")), "reloj", "closing", id="open-until-nothing"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(agrupar=[{"columna": "ordenes_compra.fecha_recibida", "por": "mes"}])), "reloj", "event or a term", id="period-of-a-closing"),
        pytest.param(changed("ventas_semana_linea", lambda b: b["linea_base"].update(columna="pedidos_detalle.valor_neto")), "reloj", "not a date of an event", id="baseline-on-a-number"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(filtro=[{"columna": "ordenes_compra.cantidad", "op": "=", "valor": "mucho"}])), "lenguaje", "not a integer", id="literal-of-another-type"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(medida={"agregado": "sum", "de": "ordenes_compra.sku"})), "lenguaje", "needs a number", id="sum-of-text"),
        pytest.param(changed("oc_abiertas", lambda b: b.update(medida={"agregado": "max", "de": {"op": "+", "izq": "ordenes_compra.fecha_oc", "der": "ordenes_compra.fecha_esperada"}})), "lenguaje", "does not apply", id="date-plus-date"),
        pytest.param(changed("ventas_semana_linea", lambda b: b.update(agrupar=["productos.linea", {"columna": "pedidos.fecha", "por": "mes"}])), "lenguaje", "own period", id="baseline-with-a-period"),
        pytest.param(changed("oc_abiertas", lambda b: b["salida"].update(valor="proveedor_id")), "lenguaje", "unique name", id="duplicate-name"),
        pytest.param(changed("oc_abiertas", lambda b: b["salida"].update(valor="dia")), "lenguaje", "unique name", id="reserved-name"),
    ],
)
def test_a_block_the_kernel_cannot_bound_is_refused_with_its_guard(block, guard, words):
    refusal = refused(block)
    assert refusal.guard == guard and words in refusal.detail, refusal


def test_a_function_reads_its_argument_and_belongs_to_the_kernel_role():
    definition = function_definition("oc_abiertas", fixture_block("oc_abiertas"), SOURCES).as_string()
    assert definition.startswith('CREATE OR REPLACE FUNCTION "centinela"."k_oc_abiertas"(dia date) RETURNS TABLE ("proveedor_id" text, "ordenes_abiertas" bigint)')
    assert "SECURITY DEFINER SET search_path = pg_catalog, pg_temp" in definition
    assert "CAST(dia AS date)" in definition and "%(dia)s" not in definition
    assert 'ALTER FUNCTION "centinela"."k_oc_abiertas"(date) OWNER TO centinela_kernel;' in definition
    assert 'REVOKE ALL ON FUNCTION "centinela"."k_oc_abiertas"(date) FROM PUBLIC;' in definition
    assert 'GRANT EXECUTE ON FUNCTION "centinela"."k_oc_abiertas"(date) TO centinela_lector;' in definition


def test_a_metric_name_outside_the_pattern_is_refused():
    with pytest.raises(Refused) as caught:
        function_definition("Oc-Abiertas", fixture_block("oc_abiertas"), SOURCES)
    assert caught.value.guard == "lenguaje"


def test_freezing_keeps_the_text_its_hash_and_the_compiler_version():
    frozen = freeze(compile_kpi(fixture_block("oc_abiertas"), SOURCES))
    assert "%(dia)s" in frozen.sql and frozen.hash == digest(frozen.sql) and frozen.compiler_version == "1"


def calls(tree, attribute):
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == attribute]


def test_every_sql_fragment_of_the_package_is_a_constant():
    for path in PACKAGE.glob("*.py"):
        for call in calls(ast.parse(path.read_text()), "SQL"):
            argument = call.args[0] if len(call.args) == 1 else None
            assert isinstance(argument, ast.Constant) and isinstance(argument.value, str), f"{path.name}:{call.lineno}"


def test_no_query_of_the_package_is_built_from_a_formatted_string():
    for path in PACKAGE.glob("*.py"):
        for call in calls(ast.parse(path.read_text()), "execute"):
            first = call.args[0]
            formatted = isinstance(first, (ast.JoinedStr, ast.BinOp)) or (
                isinstance(first, ast.Call) and isinstance(first.func, ast.Attribute) and first.func.attr == "format" and isinstance(first.func.value, ast.Constant)
            )
            assert not formatted, f"{path.name}:{call.lineno}"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_compiler.py -q`
Expected: `ModuleNotFoundError: No module named 'centinela_tools.compiler'`.

- [ ] **Step 3: Write `compiler.py`**

```python
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from psycopg import sql

from .language import check_block
from .refusal import Refused
from .sources import Join, Source, Sources, Table

COMPILER_VERSION = "1"
NAME = re.compile(r"^[a-z][a-z0-9_]{0,60}$")
NUMERIC = frozenset({"integer", "bigint", "numeric"})
RESERVED = frozenset({"dia", "periodo"})
LITERALS = {"text": (str,), "integer": (int,), "bigint": (int,), "numeric": (int, float), "boolean": (bool,), "date": (str,)}
TYPES = {
    "text": sql.SQL("text"),
    "integer": sql.SQL("integer"),
    "bigint": sql.SQL("bigint"),
    "numeric": sql.SQL("numeric"),
    "date": sql.SQL("date"),
    "boolean": sql.SQL("boolean"),
}
COMPARE = {
    "=": sql.SQL("{} = {}"),
    "!=": sql.SQL("{} <> {}"),
    "<": sql.SQL("{} < {}"),
    "<=": sql.SQL("{} <= {}"),
    ">": sql.SQL("{} > {}"),
    ">=": sql.SQL("{} >= {}"),
}
ARITH = {
    "+": sql.SQL("({}::numeric + {}::numeric)"),
    "-": sql.SQL("({}::numeric - {}::numeric)"),
    "*": sql.SQL("({}::numeric * {}::numeric)"),
    "/": sql.SQL("({}::numeric / NULLIF({}::numeric, 0))"),
}
AGGREGATE = {
    "sum": sql.SQL("sum({})::numeric"),
    "avg": sql.SQL("avg({})::numeric"),
    "mediana": sql.SQL("percentile_cont(0.5) WITHIN GROUP (ORDER BY {})::numeric"),
    "min": sql.SQL("min({})"),
    "max": sql.SQL("max({})"),
    "count": sql.SQL("count({})"),
}
TRUNC = {"semana": sql.SQL("date_trunc('week', {})::date"), "mes": sql.SQL("date_trunc('month', {})::date")}
LAST = {"semana": sql.SQL("date_trunc('week', {} - 6)::date"), "mes": sql.SQL("(date_trunc('month', {} + 1) - interval '1 month')::date")}
START = {"semana": sql.SQL("({} - 7 * {})"), "mes": sql.SQL("({} - interval '1 month' * {})::date")}
END = {"semana": sql.SQL("({} + 7)"), "mes": sql.SQL("({} + interval '1 month')::date")}
DELTA = {
    "delta": sql.SQL("(actual.valor - avg(previo.valor))::numeric"),
    "delta_pct": sql.SQL("round(100 * (actual.valor / NULLIF(avg(previo.valor), 0) - 1), 2)"),
}


@dataclass(frozen=True)
class Compiled:
    query: sql.Composable
    columns: tuple[tuple[str, str], ...]
    entity: tuple[str, ...]


@dataclass(frozen=True)
class Frozen:
    sql: str
    hash: str
    compiler_version: str


@dataclass(frozen=True)
class Scope:
    sources: Sources
    source: Source
    aliases: Mapping[str, str]
    day: sql.Composable

    def table_of(self, alias: str) -> Table:
        return self.sources.tables[self.aliases[alias]]

    def column(self, ref: str) -> tuple[str, str, str]:
        alias, _, name = ref.partition(".")
        if alias not in self.aliases:
            raise Refused("fuente", f"{ref}: {alias} is neither the source nor a join this KPI names")
        table = self.table_of(alias)
        if name in table.excluded:
            raise Refused("fuente", f"{ref} is not readable: {table.excluded[name]}")
        if name not in table.columns:
            raise Refused("fuente", f"{ref} is not a column fuentes.yaml lets the kernel read")
        return alias, name, table.columns[name]

    def role(self, ref: str) -> str | None:
        alias, name, _ = self.column(ref)
        return self.table_of(alias).dates.get(name)

    def raw(self, alias: str, name: str) -> sql.Composable:
        column = sql.Identifier(alias, name)
        if self.table_of(alias).dates.get(name) == "cierre":
            return sql.SQL("(CASE WHEN {c} <= {d} THEN {c} END)").format(c=column, d=self.day)
        return column

    def read(self, ref: str) -> tuple[sql.Composable, str]:
        alias, name, kind = self.column(ref)
        if name in self.table_of(alias).leaks:
            raise Refused("fuente", f"{ref} holds the end of the dataset; only a filter on a value known when the row is created reads it")
        return self.raw(alias, name), kind


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def freeze(compiled: Compiled) -> Frozen:
    text = compiled.query.as_string()
    return Frozen(text, digest(text), COMPILER_VERSION)


def scope_of(block: Mapping[str, Any], sources: Sources, day: sql.Composable) -> tuple[Scope, list[Join]]:
    source = sources.sources.get(block["fuente"])
    if source is None:
        raise Refused("fuente", f"fuente: {block['fuente']} is not a source fuentes.yaml declares")
    aliases = {source.name: source.name}
    joins = []
    for name in block.get("unir", []):
        join = source.joins.get(name)
        if join is None:
            raise Refused("fuente", f"unir: {name} is not a join fuentes.yaml declares for {source.name}")
        if join.origin not in aliases:
            raise Refused("fuente", f"unir: {name} joins from {join.origin}, which unir does not name before it")
        aliases[name] = join.table
        joins.append(join)
    if source.dated_by is not None and source.dated_by not in aliases:
        raise Refused("reloj", f"{source.name} has no date of its own; unir must name {source.dated_by}, which dates it")
    return Scope(sources, source, aliases, day), joins


def event_bounds(scope: Scope, alias: str) -> list[sql.Composable]:
    dates = scope.table_of(alias).dates
    return [sql.SQL("{} <= {}").format(sql.Identifier(alias, column), scope.day) for column, role in dates.items() if role == "evento"]


def from_clause(scope: Scope, joins: list[Join]) -> sql.Composable:
    parts = [sql.SQL("FROM {} AS {}").format(sql.Identifier("centinela", scope.source.name), sql.Identifier(scope.source.name))]
    for join in joins:
        on = [sql.SQL("{} = {}").format(sql.Identifier(join.origin, local), sql.Identifier(join.name, remote)) for local, remote in join.on.items()]
        on += event_bounds(scope, join.name)
        parts.append(sql.SQL("LEFT JOIN {} AS {} ON {}").format(sql.Identifier("centinela", join.table), sql.Identifier(join.name), sql.SQL(" AND ").join(on)))
    return sql.SQL(" ").join(parts)


def event_column(scope: Scope, ref: str, key: str) -> sql.Composable:
    alias, name, _ = scope.column(ref)
    if scope.table_of(alias).dates.get(name) != "evento":
        raise Refused("reloj", f"{key}: {ref} is not a date of an event, so dia cannot bound it")
    return sql.Identifier(alias, name)


def open_on_day(spec: Mapping[str, str], scope: Scope) -> list[sql.Composable]:
    start = event_column(scope, spec["desde"], "abierto_al_dia.desde")
    bounds = [sql.SQL("{} <= {}").format(start, scope.day)]
    end = spec["hasta"]
    if "." in end:
        alias, name, _ = scope.column(end)
        if scope.table_of(alias).dates.get(name) != "cierre":
            raise Refused("reloj", f"abierto_al_dia.hasta: {end} is not a date that closes a row")
        column = sql.Identifier(alias, name)
        return [*bounds, sql.SQL("({c} IS NULL OR {c} > {d})").format(c=column, d=scope.day)]
    closing = scope.source.closings.get(end)
    if closing is None:
        raise Refused("reloj", f"abierto_al_dia.hasta: {end} is neither a closing date nor a closing fuentes.yaml declares for {scope.source.name}")
    match = [sql.SQL("{} = {}").format(sql.Identifier(closing.name, child), sql.Identifier(scope.source.name, parent)) for child, parent in closing.on.items()]
    match.append(sql.SQL("{} <= {}").format(sql.Identifier(closing.name, closing.date), scope.day))
    exists = sql.SQL("NOT EXISTS (SELECT 1 FROM {} AS {} WHERE {})").format(
        sql.Identifier("centinela", closing.table), sql.Identifier(closing.name), sql.SQL(" AND ").join(match)
    )
    return [*bounds, exists]


def clock(block: Mapping[str, Any], scope: Scope) -> list[sql.Composable]:
    conditions = event_bounds(scope, scope.source.name)
    if scope.source.dated_by is not None:
        conditions += event_bounds(scope, scope.source.dated_by)
    if "ventana" in block:
        column = event_column(scope, block["ventana"]["columna"], "ventana")
        conditions.append(sql.SQL("{} > {} - {}").format(column, scope.day, sql.Literal(block["ventana"]["dias"])))
    if "abierto_al_dia" in block:
        conditions += open_on_day(block["abierto_al_dia"], scope)
    return conditions


def literal(value: Any, kind: str, ref: str) -> sql.Composable:
    if isinstance(value, bool) != (kind == "boolean") or not isinstance(value, LITERALS[kind]):
        raise Refused("lenguaje", f"filtro: {value!r} is not a {kind}, the type of {ref}")
    if kind == "date":
        try:
            date.fromisoformat(value)
        except ValueError as error:
            raise Refused("lenguaje", f"filtro: {value!r} is not a date YYYY-MM-DD") from error
    return sql.Literal(value)


def condition(spec: Mapping[str, Any], scope: Scope) -> sql.Composable:
    ref, operator, value = spec["columna"], spec["op"], spec["valor"]
    alias, name, kind = scope.column(ref)
    known = scope.table_of(alias).leaks.get(name)
    values = value if operator == "en" else [value]
    if known is not None and (operator not in ("=", "!=", "en") or not set(values) <= set(known)):
        raise Refused("fuente", f"filtro: {ref} holds the end of the dataset; only =, != or en on {list(known)} reads it")
    column = scope.raw(alias, name)
    if operator == "en":
        return sql.SQL("{} IN ({})").format(column, sql.SQL(", ").join(literal(item, kind, ref) for item in values))
    return COMPARE[operator].format(column, literal(value, kind, ref))


def expression(node: Any, scope: Scope) -> tuple[sql.Composable, str]:
    if isinstance(node, str):
        return scope.read(node)
    left, left_kind = expression(node["izq"], scope)
    right, right_kind = expression(node["der"], scope)
    if node["op"] == "-" and left_kind == right_kind == "date":
        return sql.SQL("({} - {})").format(left, right), "integer"
    if left_kind in NUMERIC and right_kind in NUMERIC:
        return ARITH[node["op"]].format(left, right), "numeric"
    raise Refused("lenguaje", f"{node['op']} does not apply to {left_kind} and {right_kind}")


def measure(spec: Mapping[str, Any], scope: Scope) -> tuple[sql.Composable, str]:
    aggregate = spec["agregado"]
    if "de" not in spec:
        return sql.SQL("count(*)"), "bigint"
    expr, kind = expression(spec["de"], scope)
    if aggregate == "count":
        return AGGREGATE["count"].format(expr), "bigint"
    if aggregate in ("min", "max"):
        return AGGREGATE[aggregate].format(expr), kind
    if kind not in NUMERIC:
        raise Refused("lenguaje", f"{aggregate} needs a number, and {spec['de']} is {kind}")
    return AGGREGATE[aggregate].format(expr), "numeric"


def value(block: Mapping[str, Any], scope: Scope) -> tuple[sql.Composable, str]:
    if "medida" in block:
        return measure(block["medida"], scope)
    numerator, numerator_kind = measure(block["razon"]["numerador"], scope)
    denominator, denominator_kind = measure(block["razon"]["denominador"], scope)
    if numerator_kind not in NUMERIC or denominator_kind not in NUMERIC:
        raise Refused("lenguaje", "razon: both measures must be numbers")
    return sql.SQL("({}::numeric / NULLIF({}::numeric, 0))").format(numerator, denominator), "numeric"


def dimension(item: Any, scope: Scope) -> tuple[str, sql.Composable, str]:
    if isinstance(item, str):
        scope.column(item)
        if item not in scope.source.dimensions:
            raise Refused("fuente", f"agrupar: {item} is not a dimension fuentes.yaml declares for {scope.source.name}")
        expr, kind = scope.read(item)
        return item.partition(".")[2], expr, kind
    ref, period = item["columna"], item["por"]
    if scope.role(ref) not in ("evento", "plazo"):
        raise Refused("reloj", f"agrupar: {ref} is not a date of an event or a term, so it has no {period}")
    expr, _ = scope.read(ref)
    return period, TRUNC[period].format(expr), "date"


def compile_kpi(block: Mapping[str, Any], sources: Sources, day: sql.Composable = sql.Placeholder("dia")) -> Compiled:
    check_block(block)
    scope, joins = scope_of(block, sources, sql.SQL("CAST({} AS date)").format(day))
    dims = [dimension(item, scope) for item in block["agrupar"]]
    names = [name for name, _, _ in dims] + list(block["salida"].values())
    if len(set(names)) != len(names) or RESERVED & set(names):
        raise Refused("lenguaje", f"agrupar and salida name {names}: each output column needs a unique name other than dia or periodo")
    measured, kind = value(block, scope)
    conditions = clock(block, scope) + [condition(spec, scope) for spec in block.get("filtro", [])]
    source = from_clause(scope, joins)
    if "linea_base" in block:
        return baseline(block, scope, dims, measured, kind, conditions, source)
    selected = [sql.SQL("{}::{} AS {}").format(expr, TYPES[k], sql.Identifier(name)) for name, expr, k in dims]
    selected.append(sql.SQL("{}::{} AS {}").format(measured, TYPES[kind], sql.Identifier(block["salida"]["valor"])))
    query = sql.SQL("SELECT {} {} WHERE {} GROUP BY {}").format(
        sql.SQL(", ").join(selected),
        source,
        sql.SQL(" AND ").join(conditions or [sql.SQL("TRUE")]),
        sql.SQL(", ").join(expr for _, expr, _ in dims),
    )
    columns = tuple((name, k) for name, _, k in dims) + ((block["salida"]["valor"], kind),)
    return Compiled(query, columns, tuple(name for name, _, _ in dims))


def baseline(block, scope, dims, measured, kind, conditions, source) -> Compiled:
    spec = block["linea_base"]
    if kind not in NUMERIC:
        raise Refused("lenguaje", "linea_base: the measure must be a number")
    if any(not isinstance(item, str) for item in block["agrupar"]):
        raise Refused("lenguaje", "linea_base groups by its own period; agrupar may not hold another")
    period = spec["periodo"]
    column = event_column(scope, spec["columna"], "linea_base")
    current = LAST[period].format(scope.day)
    bounds = [
        sql.SQL("{} >= {}").format(column, START[period].format(current, sql.Literal(spec["n"]))),
        sql.SQL("{} < {}").format(column, END[period].format(current)),
    ]
    truncated = TRUNC[period].format(column)
    inner = sql.SQL("SELECT {dims}, {period} AS periodo, {value} AS valor {source} WHERE {where} GROUP BY {group}").format(
        dims=sql.SQL(", ").join(sql.SQL("{} AS {}").format(expr, sql.Identifier(name)) for name, expr, _ in dims),
        period=truncated,
        value=measured,
        source=source,
        where=sql.SQL(" AND ").join(conditions + bounds),
        group=sql.SQL(", ").join([expr for _, expr, _ in dims] + [truncated]),
    )
    same = sql.SQL(" AND ").join(
        sql.SQL("{} IS NOT DISTINCT FROM {}").format(sql.Identifier("actual", name), sql.Identifier("previo", name)) for name, _, _ in dims
    )
    out = block["salida"]
    query = sql.SQL(
        "WITH periodos AS ({inner}) SELECT {dims}, actual.valor::numeric AS {valor}, avg(previo.valor)::numeric AS {base}, {delta} AS {delta_name} "
        "FROM periodos AS actual JOIN periodos AS previo ON {same} AND previo.periodo < actual.periodo "
        "WHERE actual.periodo = {current} GROUP BY {group}, actual.valor"
    ).format(
        inner=inner,
        dims=sql.SQL(", ").join(sql.SQL("{}::{} AS {}").format(sql.Identifier("actual", name), TYPES[k], sql.Identifier(name)) for name, _, k in dims),
        valor=sql.Identifier(out["valor"]),
        base=sql.Identifier(out["base"]),
        delta=DELTA[spec["salida"]],
        delta_name=sql.Identifier(out["delta"]),
        same=same,
        current=current,
        group=sql.SQL(", ").join(sql.Identifier("actual", name) for name, _, _ in dims),
    )
    columns = tuple((name, k) for name, _, k in dims) + ((out["valor"], "numeric"), (out["base"], "numeric"), (out["delta"], "numeric"))
    return Compiled(query, columns, tuple(name for name, _, _ in dims))


def function_definition(metric: str, block: Mapping[str, Any], sources: Sources) -> sql.Composable:
    if NAME.match(metric) is None:
        raise Refused("lenguaje", f"{metric} is not a metric name of lowercase letters, digits and underscores")
    compiled = compile_kpi(block, sources, day=sql.SQL("dia"))
    function = sql.Identifier("centinela", f"k_{metric}")
    returns = sql.SQL(", ").join(sql.SQL("{} {}").format(sql.Identifier(name), TYPES[kind]) for name, kind in compiled.columns)
    return sql.SQL(
        "CREATE OR REPLACE FUNCTION {fn}(dia date) RETURNS TABLE ({returns}) LANGUAGE sql STABLE SECURITY DEFINER "
        "SET search_path = pg_catalog, pg_temp AS {body};\n"
        "ALTER FUNCTION {fn}(date) OWNER TO centinela_kernel;\n"
        "REVOKE ALL ON FUNCTION {fn}(date) FROM PUBLIC;\n"
        "GRANT EXECUTE ON FUNCTION {fn}(date) TO centinela_lector;\n"
    ).format(fn=function, returns=returns, body=sql.Literal(compiled.query.as_string()))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_compiler.py tests/test_language.py tests/test_sources.py -q`
Expected: all pass. If a string assertion fails on quoting or spacing, print `text(...)`. If the clock condition is truly absent, fix the compiler. If only psycopg's rendering differs (for example `%(dia)s`), fix the expected literal to the rendered form and keep every fragment the test asserts.

- [ ] **Step 5: Ask the user, then commit**

```bash
git add packages/tools
git commit -q -F - <<'MSG'
Compile a kernel: block to psycopg.sql composition that takes the simulated day, refusing what it cannot bound with the guard named

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 5: The roles, the generated file, the compose, and the scratch database

**Files:**
- Create: `packages/tools/centinela_tools/{settings,generate}.py`, the first part of `packages/tools/centinela_tools/tools.py` (`load_entries`, `planner_cost`), `packages/tools/tests/conftest.py`, `packages/tools/tests/test_generate.py`, `packages/tools/tests/test_roles.py`
- Generated: `data/sql/05_kpis.generated.sql`
- Modify: `data/docker-compose.yml`

**Interfaces:**
- Consumes: `compiler.compile_kpi`, `compiler.function_definition`, `language.check_card`, `sources.load_sources`
- Produces:
  - `settings.Settings(max_cost: float = 1_000_000.0, timeout_ms: int = 5_000, max_groups: int = 20_000, sample_rows: int = 20)` and `Settings.from_env(env: Mapping[str, str] = os.environ) -> Settings`
  - `tools.load_entries(path: Path) -> dict[str, dict]` (the `metricas:` mapping)
  - `tools.planner_cost(conn, query: sql.Composable, day: date) -> float`
  - `generate.view_names(sql_dir: Path) -> list[str]`, `generate.render(sources, entries, views, cost: Callable[[sql.Composable], float], settings) -> str`, `generate.main() -> None`
  - the `db` fixtures `superuser`, `connect` (a `Callable[[str], psycopg.Connection]` for the roles `lector` and `kernel`), and the constant `DSN`

- [ ] **Step 1: Write the failing static tests**

`packages/tools/tests/test_generate.py`:

```python
# The generator of data/sql/05_kpis.generated.sql: the committed file is exactly what it writes from
# the tree, so a hand edit fails here; the roles, the column grants and a function are written as
# the kernel's page says; and a KPI over the planner's cap is refused by the guard costo.
import pytest

from centinela_tools.generate import render, view_names
from centinela_tools.paths import GENERATED, METRICAS, SQL_DIR
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import load_entries

from support import fixture_entries

SOURCES = load_sources()


def no_database(query):
    raise AssertionError("no entry of data/metricas.yaml carries kernel:, so no cost is estimated")


def test_the_committed_file_is_what_the_generator_writes():
    assert GENERATED.read_text() == render(SOURCES, load_entries(METRICAS), view_names(SQL_DIR), no_database, Settings())


def test_the_view_names_come_from_both_view_files():
    names = view_names(SQL_DIR)
    assert "v_ventas" in names and "v_costo_sku" in names and len(names) == len(set(names))


def test_the_file_opens_with_its_banner_and_grants_column_by_column():
    text = render(SOURCES, {}, view_names(SQL_DIR), no_database, Settings())
    assert text.startswith("-- Written by `uv run python -m centinela_tools.generate`")
    assert 'GRANT SELECT ("vendedor_id", "region") ON "centinela"."vendedores" TO centinela_kernel;' in text
    assert 'GRANT SELECT ON "centinela"."v_ventas" TO centinela_lector;' in text
    assert "ALTER FUNCTION centinela.fecha_corte() SECURITY DEFINER" in text
    assert "CREATE OR REPLACE FUNCTION" not in text


def test_a_fixture_kpi_becomes_a_function():
    text = render(SOURCES, fixture_entries(), view_names(SQL_DIR), lambda query: 1.0, Settings())
    assert text.count("CREATE OR REPLACE FUNCTION") == 3


def test_a_kpi_over_the_cost_cap_is_refused():
    with pytest.raises(Refused) as refused:
        render(SOURCES, fixture_entries(), view_names(SQL_DIR), lambda query: 2.0, Settings(max_cost=1.0))
    assert refused.value.guard == "costo"


def test_the_settings_read_the_environment():
    settings = Settings.from_env({"CENTINELA_KERNEL_COSTO_MAX": "10", "CENTINELA_KERNEL_TIMEOUT_MS": "20", "CENTINELA_KERNEL_GRUPOS_MAX": "30", "CENTINELA_KERNEL_MUESTRA": "4"})
    assert settings == Settings(10.0, 20, 30, 4)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_generate.py -q`
Expected: `ModuleNotFoundError: No module named 'centinela_tools.generate'`.

- [ ] **Step 3: Write `settings.py`, the first part of `tools.py`, and `generate.py`**

```python
import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    max_cost: float = 1_000_000.0
    timeout_ms: int = 5_000
    max_groups: int = 20_000
    sample_rows: int = 20

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        default = cls()
        return cls(
            float(env.get("CENTINELA_KERNEL_COSTO_MAX", default.max_cost)),
            int(env.get("CENTINELA_KERNEL_TIMEOUT_MS", default.timeout_ms)),
            int(env.get("CENTINELA_KERNEL_GRUPOS_MAX", default.max_groups)),
            int(env.get("CENTINELA_KERNEL_MUESTRA", default.sample_rows)),
        )
```

`tools.py` (first part; Task 6 adds the rest):

```python
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
```

`generate.py`:

```python
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
  EXECUTE format('REVOKE TEMPORARY ON DATABASE %I FROM PUBLIC', current_database());
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO centinela_lector, centinela_kernel', current_database());
END
$roles$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA centinela TO centinela_lector, centinela_kernel;
"""
FECHA_CORTE = """ALTER FUNCTION centinela.fecha_corte() SECURITY DEFINER SET search_path = centinela, pg_temp;
ALTER FUNCTION centinela.fecha_corte() OWNER TO centinela_kernel;
"""


def view_names(sql_dir: Path) -> list[str]:
    names = []
    for name in ("03_capa_semantica.sql", "04_vistas_causa.sql"):
        names += re.findall(r"CREATE OR REPLACE VIEW (v_[a-z_]+)", (sql_dir / name).read_text())
    return names


def render(sources: Sources, entries: Mapping[str, Mapping[str, Any]], views: list[str], cost: Callable[[sql.Composable], float], settings: Settings) -> str:
    parts = [BANNER, ROLES]
    for name, table in sources.tables.items():
        grant = sql.SQL("GRANT SELECT ({}) ON {} TO centinela_kernel;\n").format(
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
```

- [ ] **Step 4: Generate the file and run the static tests**

Run: `uv run python -m centinela_tools.generate && uv run pytest tests/test_generate.py -q`
Expected: `data/sql/05_kpis.generated.sql` exists with the banner, the roles and the grants, and no function. All tests pass.

- [ ] **Step 5: Mount `05` in the compose**

In `data/docker-compose.yml`, add `- ./sql/05_kpis.generated.sql:/docker-entrypoint-initdb.d/05_kpis.generated.sql:ro` after the `04` line. In its header, change "runs `sql/01_esquema.sql`, ... and `sql/04_vistas_causa.sql`" to also name `sql/05_kpis.generated.sql`.

- [ ] **Step 6: Start the scratch database**

Run from `packages/tools/`:

```bash
docker run -d --rm --name centinela-kernel-test -p 55432:5432 \
  -e POSTGRES_DB=centinela -e POSTGRES_USER=centinela -e POSTGRES_PASSWORD=centinela \
  -v "$PWD/../../data/sql/01_esquema.sql:/docker-entrypoint-initdb.d/01_esquema.sql:ro" \
  -v "$PWD/../../data/sql/02_carga.sql:/docker-entrypoint-initdb.d/02_carga.sql:ro" \
  -v "$PWD/../../data/sql/03_capa_semantica.sql:/docker-entrypoint-initdb.d/03_capa_semantica.sql:ro" \
  -v "$PWD/../../data/sql/04_vistas_causa.sql:/docker-entrypoint-initdb.d/04_vistas_causa.sql:ro" \
  -v "$PWD/../../data/csv:/csv:ro" postgres:16-alpine
```

Wait until `docker exec centinela-kernel-test psql -U centinela -d centinela -h 127.0.0.1 -tAc 'SELECT count(*) FROM centinela.v_ventas'` prints a number. Use the Monitor tool with an until-loop, never a foreground `sleep`. Then `export CENTINELA_TEST_DSN=postgresql://centinela:centinela@localhost:55432/centinela`.

- [ ] **Step 7: Write the `db` fixtures and the failing role tests**

`packages/tools/tests/conftest.py`:

```python
# Fixtures for the tests marked db. They run only when CENTINELA_TEST_DSN names a scratch PostgreSQL
# loaded with data/sql/01 to 04 (packages/tools/AGENTS.md starts one); the session applies to it the
# roles, the grants and the fixture KPIs of tests/fixtures/metricas.yaml, as the generator writes them.
import os

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from centinela_tools.generate import render, view_names
from centinela_tools.paths import SQL_DIR
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources

from support import fixture_entries

DSN = os.environ.get("CENTINELA_TEST_DSN")
ROLES = {"lector": "centinela_lector", "kernel": "centinela_kernel"}


def pytest_collection_modifyitems(config, items):
    if DSN:
        return
    skip = pytest.mark.skip(reason="CENTINELA_TEST_DSN is not set; packages/tools/AGENTS.md starts a scratch database")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


def open_as(role: str) -> psycopg.Connection:
    name = ROLES[role]
    return psycopg.connect(make_conninfo(DSN, user=name, password=name), autocommit=True)


@pytest.fixture(scope="session")
def applied():
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(render(load_sources(), fixture_entries(), view_names(SQL_DIR), lambda query: 0.0, Settings()))
    return True


@pytest.fixture
def superuser(applied):
    with psycopg.connect(DSN, autocommit=True) as conn:
        yield conn


@pytest.fixture
def connect(applied):
    return open_as
```

`packages/tools/tests/test_roles.py`:

```python
# The gate of the law that no agent changes a database: what centinela_lector and centinela_kernel
# can read and run, and that every write either role attempts fails. Needs the scratch database.
import psycopg
import pytest

pytestmark = pytest.mark.db

WRITES = [
    "INSERT INTO centinela.bodegas VALUES ('X', 'X', 'X')",
    "UPDATE centinela.pedidos SET canal = 'x'",
    "DELETE FROM centinela.pagos",
    "TRUNCATE centinela.pagos",
    "CREATE TABLE centinela.intruso (x int)",
    "CREATE TABLE public.intruso (x int)",
    "CREATE TEMP TABLE intruso (x int)",
]


def fails(conn, statement):
    with pytest.raises(psycopg.Error):
        conn.execute(statement)


def test_the_reader_cannot_select_a_table(connect):
    with connect("lector") as conn:
        fails(conn, "SELECT * FROM centinela.pedidos LIMIT 1")


def test_the_reader_reads_a_view_that_calls_fecha_corte(connect):
    with connect("lector") as conn:
        assert conn.execute("SELECT count(*) FROM centinela.v_cartera_cliente").fetchone()[0] > 0


def test_the_reader_executes_a_kernel_function(connect):
    with connect("lector") as conn:
        assert conn.execute("SELECT count(*) FROM centinela.k_oc_abiertas('2026-03-02')").fetchone()[0] > 0


def test_the_kernel_reads_a_readable_column_and_not_a_persons_name(connect):
    with connect("kernel") as conn:
        conn.execute("SELECT vendedor_id, region FROM centinela.vendedores LIMIT 1")
        fails(conn, "SELECT nombre FROM centinela.vendedores LIMIT 1")


def test_the_kernel_cannot_read_a_view(connect):
    with connect("kernel") as conn:
        fails(conn, "SELECT * FROM centinela.v_ventas LIMIT 1")


@pytest.mark.parametrize("role", ["lector", "kernel"])
@pytest.mark.parametrize("statement", WRITES)
def test_every_write_of_either_role_fails(connect, superuser, role, statement):
    before = superuser.execute("SELECT (SELECT count(*) FROM centinela.pagos), (SELECT count(*) FROM centinela.bodegas)").fetchone()
    with connect(role) as conn:
        fails(conn, statement)
    assert superuser.execute("SELECT (SELECT count(*) FROM centinela.pagos), (SELECT count(*) FROM centinela.bodegas)").fetchone() == before
```

- [ ] **Step 8: Run the role tests**

Run: `uv run pytest -m db tests/test_roles.py -q`
Expected: all pass. If `test_the_reader_reads_a_view_that_calls_fecha_corte` fails with permission denied, the `FECHA_CORTE` block did not apply: fix the generator. If a write succeeds, find the grant that allowed it, remove it in `ROLES`, regenerate, and drop and restart the container.

- [ ] **Step 9: Run every test, then ask the user, then commit**

Run: `uv run pytest -q`
Expected: all pass, the `db` ones included.

```bash
git add packages/tools data/sql/05_kpis.generated.sql data/docker-compose.yml
git commit -q -F - <<'MSG'
Generate the kernel's roles and grants into 05_kpis.generated.sql, so no role a tool holds can write and the reader reaches only views and k_ functions

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 6: The four tools and the guards that need a database

**Files:**
- Modify: `packages/tools/centinela_tools/tools.py`
- Create: `packages/tools/tests/test_tools.py` (static), `packages/tools/tests/test_tools_db.py`

**Interfaces:**
- Consumes: `compiler.compile_kpi`, `compiler.freeze`, `compiler.digest`, `compiler.NAME`, `language.check_card`, `settings.Settings`, `tools.planner_cost`
- Produces:
  - `tools.Kpi(id, origin, card, descriptive, entity, columns, sql=None, hash=None, compiler_version=None)` and `tools.Catalogue(kpis: Mapping[str, Kpi])`
  - `tools.catalogue_of(entries, sources, approved: Iterable[Mapping] = ()) -> Catalogue`. An approved record is `{id, sql, hash, version_compilador, ficha, descriptivo, entidad, columnas: [{nombre, tipo}]}`.
  - `tools.Connect = Callable[[str], psycopg.Connection]`, called with `"lector"` or `"kernel"`. It returns an autocommit connection, which the tool closes.
  - `tools.kpi_validar(block, day, sources, connect, settings) -> dict` with `sql`, `hash`, `version_compilador`, `entidad`, `columnas` and `costo`
  - `tools.kpi_dry_run(block, day, sources, connect, settings) -> dict`, which is `kpi_validar` plus `dia`, `filas`, `total_filas` and `ms`
  - `tools.kpi_consultar(kpi_id, day, catalogue, connect, settings) -> dict` with `kpi`, `dia`, `consulta` and `filas`
  - `tools.kpi_catalogo(catalogue) -> list[dict]`

- [ ] **Step 1: Write the failing static tests**

`packages/tools/tests/test_tools.py`:

```python
# The tools with no database: the catalogue built from metricas.yaml entries and approved records,
# and the refusals that must happen before any connection opens (hash, catalogo, lenguaje).
from datetime import date

import pytest

from centinela_tools.compiler import compile_kpi, freeze
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_catalogo, kpi_consultar, kpi_validar

from support import fixture_block, fixture_entries

SOURCES = load_sources()
DAY = date(2026, 3, 2)


def never(role):
    raise AssertionError("a refusal before any SQL opens no connection")


def approved(kpi_id="aprobado_oc", tamper=False):
    frozen = freeze(compile_kpi(fixture_block("oc_abiertas"), SOURCES))
    entry = fixture_entries()["oc_abiertas"]
    return {
        "id": kpi_id,
        "sql": frozen.sql + (" " if tamper else ""),
        "hash": frozen.hash,
        "version_compilador": frozen.compiler_version,
        "ficha": {key: entry[key] for key in ("descripcion", "unidad", "rango", "tendencia", "temporalidad", "audiencia")},
        "descriptivo": True,
        "entidad": ["proveedor_id"],
        "columnas": [{"nombre": "proveedor_id", "tipo": "text"}, {"nombre": "ordenes_abiertas", "tipo": "bigint"}],
    }


def test_the_catalogue_lists_entries_with_a_block_and_approved_records():
    entries = {**fixture_entries(), "sin_bloque": {"descripcion": "no compila"}}
    listed = {kpi["id"]: kpi for kpi in kpi_catalogo(catalogue_of(entries, SOURCES, [approved()]))}
    assert set(listed) == {"oc_abiertas", "facturas_abiertas", "ventas_semana_linea", "aprobado_oc"}
    assert listed["oc_abiertas"]["descriptivo"] is True and listed["facturas_abiertas"]["descriptivo"] is False
    assert listed["aprobado_oc"]["origen"] == "aprobado"
    assert listed["ventas_semana_linea"]["entidad"] == ["linea"]
    assert listed["oc_abiertas"]["ficha"]["tendencia"] == "menor_es_mejor"


def test_an_approved_kpi_whose_text_no_longer_matches_its_hash_is_refused():
    catalogue = catalogue_of({}, SOURCES, [approved(tamper=True)])
    with pytest.raises(Refused) as refused:
        kpi_consultar("aprobado_oc", DAY, catalogue, never, Settings())
    assert refused.value.guard == "hash"


def test_a_kpi_in_no_catalogue_is_refused():
    with pytest.raises(Refused) as refused:
        kpi_consultar("inventado", DAY, catalogue_of({}, SOURCES), never, Settings())
    assert refused.value.guard == "catalogo"


def test_a_block_outside_the_language_is_refused_before_connecting():
    block = fixture_block("oc_abiertas")
    block["unir"] = ["proveedores", "productos", "proveedores", "productos"]
    with pytest.raises(Refused) as refused:
        kpi_validar(block, DAY, SOURCES, never, Settings())
    assert refused.value.guard == "lenguaje"


def test_an_approved_id_that_clashes_with_a_base_kpi_fails_the_catalogue():
    with pytest.raises(ValueError):
        catalogue_of(fixture_entries(), SOURCES, [approved("oc_abiertas")])
```

- [ ] **Step 2: Write the failing `db` tests**

`packages/tools/tests/test_tools_db.py`:

```python
# The tools against the scratch database: each fixture KPI agrees with a hand-written as-of query on
# several simulated days, facturas_abiertas agrees with the kit's v_cartera_cliente on fecha_corte(),
# and each guard that needs a database (costo, tiempo, cardinalidad, the read-only transaction) holds.
from datetime import date

import psycopg
import pytest

from centinela_tools.compiler import compile_kpi, digest, freeze
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_consultar, kpi_dry_run, kpi_validar

from support import fixture_block, fixture_entries

pytestmark = pytest.mark.db
SOURCES = load_sources()
CATALOGUE = catalogue_of(fixture_entries(), SOURCES)
DAYS = [date(2025, 12, 15), date(2026, 3, 2), date(2026, 9, 30)]


def rows(superuser, query, params):
    return {row[0]: float(row[1]) for row in superuser.execute(query, params).fetchall()}


def kernel_rows(connect, kpi_id, day, column):
    answer = kpi_consultar(kpi_id, day, CATALOGUE, connect, Settings())
    return {list(row.values())[0]: float(row[column]) for row in answer["filas"]}


@pytest.mark.parametrize("day", DAYS)
def test_open_orders_agree_with_an_as_of_query(connect, superuser, day):
    expected = rows(superuser, "SELECT proveedor_id, count(*) FROM centinela.ordenes_compra WHERE fecha_oc <= %(d)s AND (fecha_recibida IS NULL OR fecha_recibida > %(d)s) GROUP BY 1", {"d": day})
    assert kernel_rows(connect, "oc_abiertas", day, "ordenes_abiertas") == expected


@pytest.mark.parametrize("day", DAYS)
def test_open_invoices_agree_with_an_as_of_query(connect, superuser, day):
    query = (
        "SELECT f.cliente_id, sum(f.valor_total) FROM centinela.facturas f WHERE f.fecha_factura <= %(d)s "
        "AND coalesce((SELECT min(p.fecha_pago) FROM centinela.pagos p WHERE p.factura_id = f.factura_id), 'infinity') > %(d)s GROUP BY 1"
    )
    assert kernel_rows(connect, "facturas_abiertas", day, "saldo_abierto") == pytest.approx(rows(superuser, query, {"d": day}))


def test_open_invoices_agree_with_the_kits_view_on_fecha_corte(connect, superuser):
    cut = superuser.execute("SELECT centinela.fecha_corte()").fetchone()[0]
    view = rows(superuser, "SELECT cliente_id, saldo_abierto FROM centinela.v_cartera_cliente WHERE saldo_abierto > 0", {})
    assert kernel_rows(connect, "facturas_abiertas", cut, "saldo_abierto") == pytest.approx(view)


@pytest.mark.parametrize("day, week", [(date(2026, 2, 28), date(2026, 2, 16)), (date(2026, 3, 1), date(2026, 2, 23)), (date(2026, 3, 4), date(2026, 2, 23))])
def test_a_weekly_baseline_measures_the_last_complete_week(connect, superuser, day, week):
    query = (
        "WITH w AS (SELECT date_trunc('week', p.fecha)::date AS s, pr.linea, sum(d.valor_neto) AS v FROM centinela.pedidos p "
        "JOIN centinela.pedidos_detalle d USING (pedido_id) JOIN centinela.productos pr USING (sku) "
        "WHERE p.estado <> 'Cancelado' AND p.fecha >= %(w)s::date - 56 AND p.fecha < %(w)s::date + 7 GROUP BY 1, 2) "
        "SELECT linea, max(v) FILTER (WHERE s = %(w)s), avg(v) FILTER (WHERE s < %(w)s) FROM w GROUP BY linea "
        "HAVING max(v) FILTER (WHERE s = %(w)s) IS NOT NULL AND count(*) FILTER (WHERE s < %(w)s) > 0"
    )
    expected = {row[0]: (float(row[1]), float(row[2])) for row in superuser.execute(query, {"w": week}).fetchall()}
    answer = kpi_consultar("ventas_semana_linea", day, CATALOGUE, connect, Settings())
    got = {row["linea"]: (row["ventas"], row["ventas_base"]) for row in answer["filas"]}
    assert got == pytest.approx(expected)


def test_a_day_before_the_dataset_returns_no_rows(connect):
    for kpi_id in ("oc_abiertas", "facturas_abiertas", "ventas_semana_linea"):
        assert kpi_consultar(kpi_id, date(2025, 9, 1), CATALOGUE, connect, Settings())["filas"] == []


def test_a_dry_run_returns_a_sample_the_count_and_the_time(connect):
    answer = kpi_dry_run(fixture_block("oc_abiertas"), date(2026, 3, 2), SOURCES, connect, Settings(sample_rows=2))
    assert len(answer["filas"]) <= 2 and answer["total_filas"] >= len(answer["filas"]) and answer["ms"] >= 0
    assert answer["hash"] and "%(dia)s" in answer["sql"]


def test_the_cost_guard_refuses_over_its_cap(connect):
    with pytest.raises(Refused) as refused:
        kpi_validar(fixture_block("ventas_semana_linea"), date(2026, 3, 2), SOURCES, connect, Settings(max_cost=1.0))
    assert refused.value.guard == "costo"


def test_the_time_guard_refuses_past_its_timeout(connect):
    with pytest.raises(Refused) as refused:
        kpi_dry_run(fixture_block("ventas_semana_linea"), date(2026, 3, 2), SOURCES, connect, Settings(timeout_ms=1))
    assert refused.value.guard == "tiempo"


def test_the_cardinality_guard_refuses_too_many_groups(connect):
    with pytest.raises(Refused) as refused:
        kpi_dry_run(fixture_block("oc_abiertas"), date(2026, 3, 2), SOURCES, connect, Settings(max_groups=1))
    assert refused.value.guard == "cardinalidad"


def test_a_literal_with_sql_in_it_stays_a_literal(connect, superuser):
    block = fixture_block("oc_abiertas")
    block["filtro"] = [{"columna": "ordenes_compra.sku", "op": "=", "valor": "x'); DROP TABLE centinela.pagos; --"}]
    assert kpi_dry_run(block, date(2026, 3, 2), SOURCES, connect, Settings())["total_filas"] == 0
    assert superuser.execute("SELECT count(*) FROM centinela.pagos").fetchone()[0] > 0


def test_an_approved_kpi_runs_its_stored_text_as_the_kernel_role(connect):
    frozen = freeze(compile_kpi(fixture_block("oc_abiertas"), SOURCES))
    record = {"id": "aprobado_oc", "sql": frozen.sql, "hash": frozen.hash, "version_compilador": "1", "ficha": {}, "descriptivo": True, "entidad": ["proveedor_id"], "columnas": []}
    answer = kpi_consultar("aprobado_oc", date(2026, 3, 2), catalogue_of({}, SOURCES, [record]), connect, Settings())
    assert answer["consulta"] == frozen.sql and answer["filas"]


def test_an_approved_kpi_that_writes_fails_and_changes_nothing(connect, superuser):
    text = "DELETE FROM centinela.pedidos WHERE fecha <= %(dia)s"
    record = {"id": "malicioso", "sql": text, "hash": digest(text), "version_compilador": "1", "ficha": {}, "descriptivo": True, "entidad": [], "columnas": []}
    before = superuser.execute("SELECT count(*) FROM centinela.pedidos").fetchone()[0]
    with pytest.raises(psycopg.Error):
        kpi_consultar("malicioso", date(2026, 3, 2), catalogue_of({}, SOURCES, [record]), connect, Settings())
    assert superuser.execute("SELECT count(*) FROM centinela.pedidos").fetchone()[0] == before
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_tools.py tests/test_tools_db.py -q`
Expected: `ImportError: cannot import name 'catalogue_of'`.

- [ ] **Step 4: Complete `tools.py`**

Replace its imports with the ones below and append the rest. Keep `load_entries` and `planner_cost`.

```python
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

import psycopg
import yaml
from psycopg import ClientCursor, sql
from psycopg.rows import dict_row

from .compiler import NAME, compile_kpi, digest, freeze
from .language import check_card
from .refusal import Refused
from .settings import Settings
from .sources import Sources

Connect = Callable[[str], psycopg.Connection]
CARD = ("descripcion", "unidad", "rango", "tendencia", "temporalidad", "audiencia")


@dataclass(frozen=True)
class Kpi:
    id: str
    origin: str
    card: Mapping[str, Any]
    descriptive: bool
    entity: tuple[str, ...]
    columns: tuple[tuple[str, str], ...]
    sql: str | None = None
    hash: str | None = None
    compiler_version: str | None = None


@dataclass(frozen=True)
class Catalogue:
    kpis: Mapping[str, Kpi]


def named(kpi_id: str) -> str:
    if NAME.match(kpi_id) is None:
        raise Refused("lenguaje", f"{kpi_id} is not a KPI id of lowercase letters, digits and underscores")
    return kpi_id


def catalogue_of(entries: Mapping[str, Mapping[str, Any]], sources: Sources, approved: Iterable[Mapping[str, Any]] = ()) -> Catalogue:
    kpis = {}
    for kpi_id, entry in entries.items():
        if "kernel" not in entry:
            continue
        check_card(entry)
        compiled = compile_kpi(entry["kernel"], sources)
        kpis[named(kpi_id)] = Kpi(kpi_id, "base", {key: entry[key] for key in CARD}, not entry.get("fuente_umbral"), compiled.entity, compiled.columns)
    for record in approved:
        if record["id"] in kpis:
            raise ValueError(f"{record['id']} is both a base and an approved KPI")
        kpis[named(record["id"])] = Kpi(
            record["id"], "aprobado", dict(record["ficha"]), bool(record["descriptivo"]), tuple(record["entidad"]),
            tuple((column["nombre"], column["tipo"]) for column in record["columnas"]),
            record["sql"], record["hash"], record["version_compilador"],
        )
    return Catalogue(kpis)


def plain(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: float(value) if isinstance(value, Decimal) else value.isoformat() if isinstance(value, date) else value for key, value in row.items()}


@contextmanager
def guarded(conn: psycopg.Connection, settings: Settings) -> Iterator[psycopg.Connection]:
    try:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute(sql.SQL("SET LOCAL statement_timeout = {}").format(sql.Literal(settings.timeout_ms)))
            yield conn
    except psycopg.errors.QueryCanceled as error:
        raise Refused("tiempo", f"the run passed the statement_timeout of {settings.timeout_ms} ms") from error


def kpi_validar(block: Mapping[str, Any], day: date, sources: Sources, connect: Connect, settings: Settings) -> dict[str, Any]:
    compiled = compile_kpi(block, sources)
    with connect("kernel") as conn, guarded(conn, settings):
        cost = planner_cost(conn, compiled.query, day)
    if cost > settings.max_cost:
        raise Refused("costo", f"the planner estimates {cost:.0f}, over the cap of {settings.max_cost:.0f}")
    frozen = freeze(compiled)
    return {
        "sql": frozen.sql,
        "hash": frozen.hash,
        "version_compilador": frozen.compiler_version,
        "entidad": list(compiled.entity),
        "columnas": [{"nombre": name, "tipo": kind} for name, kind in compiled.columns],
        "costo": cost,
    }


def kpi_dry_run(block: Mapping[str, Any], day: date, sources: Sources, connect: Connect, settings: Settings) -> dict[str, Any]:
    validated = kpi_validar(block, day, sources, connect, settings)
    compiled = compile_kpi(block, sources)
    started = time.perf_counter()
    with connect("kernel") as conn, guarded(conn, settings), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(compiled.query, {"dia": day})
        found = cursor.fetchmany(settings.max_groups + 1)
    elapsed = round((time.perf_counter() - started) * 1000)
    if len(found) > settings.max_groups:
        raise Refused("cardinalidad", f"the KPI returns more than {settings.max_groups} groups")
    return {**validated, "dia": day.isoformat(), "filas": [plain(row) for row in found[: settings.sample_rows]], "total_filas": len(found), "ms": elapsed}


def kpi_consultar(kpi_id: str, day: date, catalogue: Catalogue, connect: Connect, settings: Settings) -> dict[str, Any]:
    kpi = catalogue.kpis.get(kpi_id)
    if kpi is None:
        raise Refused("catalogo", f"{kpi_id} is no KPI of this client's catalogue")
    if kpi.origin == "base":
        query = sql.SQL("SELECT * FROM {}({})").format(sql.Identifier("centinela", f"k_{kpi.id}"), sql.Placeholder("dia"))
        role, text = "lector", query.as_string()
    else:
        if digest(kpi.sql) != kpi.hash:
            raise Refused("hash", f"the stored SQL of {kpi_id} does not match the hash recorded at its approval")
        query, role, text = kpi.sql, "kernel", kpi.sql
    with connect(role) as conn, guarded(conn, settings), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, {"dia": day})
        found = cursor.fetchall()
    return {"kpi": kpi_id, "dia": day.isoformat(), "consulta": text, "filas": [plain(row) for row in found]}


def kpi_catalogo(catalogue: Catalogue) -> list[dict[str, Any]]:
    return [
        {
            "id": kpi.id,
            "origen": kpi.origin,
            "ficha": dict(kpi.card),
            "descriptivo": kpi.descriptive,
            "entidad": list(kpi.entity),
            "columnas": [{"nombre": name, "tipo": kind} for name, kind in kpi.columns],
        }
        for kpi in catalogue.kpis.values()
    ]
```

The approved record of `test_an_approved_kpi_runs_its_stored_text_as_the_kernel_role` passes `"ficha": {}`. `catalogue_of` does not run `check_card` on approved records, because `apps/api` checked the card at approval (spec 6).

- [ ] **Step 5: Run every test**

Run: `uv run pytest -q`
Expected: all pass. If `test_the_time_guard_refuses_past_its_timeout` passes intermittently because the query finishes in under 1 ms, use the heaviest fixture over a 52-week `n` in that test only. Never remove it.

- [ ] **Step 6: Size the cost cap and record the measurement**

Run: `docker exec centinela-kernel-test psql -U centinela -d centinela -tAc "EXPLAIN (FORMAT JSON) SELECT * FROM centinela.v_cartera_cliente" | grep -o '"Total Cost": [0-9.]*' | head -1`
Do the same for `v_actividad_cliente` and `v_cobertura_inventario`. If ten times the largest of those exceeds `Settings.max_cost`, raise the default to ten times that cost, rounded up to a power of ten. Write the measured costs and the reason into Task 8's guard table.

- [ ] **Step 7: Ask the user, then commit**

```bash
git add packages/tools
git commit -q -F - <<'MSG'
Build the kernel's four read-only tools, each refusing with its guard named, and an approved KPI only when its stored SQL matches its hash

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 7: The MCP server

**Files:**
- Create: `packages/tools/centinela_tools/server.py`, `packages/tools/tests/test_server.py`

**Interfaces:**
- Consumes: `tools.*`, `sources.load_sources`, `settings.Settings`, `paths.METRICAS`
- Produces:
  - `server.answer(call: Callable[[], Any]) -> Any`, which turns a `Refused` into `{"rechazado": {"guarda", "detalle"}}`
  - `server.day_of(text: str) -> date`, which raises `Refused("lenguaje")` on a bad date
  - `server.build_server(sources, catalogue, settings, connect) -> FastMCP` with the tools `kpi_validar(bloque: dict, dia: str)`, `kpi_dry_run(bloque: dict, dia: str)`, `kpi_consultar(kpi: str, dia: str)` and `kpi_catalogo()`
  - `server.main(env=os.environ)`, which reads `CENTINELA_LECTOR_DSN`, `CENTINELA_KERNEL_DSN` and the optional `CENTINELA_KPIS_APROBADOS` (a path to a JSON list of approved records), then serves over stdio

- [ ] **Step 1: Write the failing tests**

`packages/tools/tests/test_server.py`:

```python
# The kernel's MCP server: exactly the four read-only tools, none of which takes SQL from a model,
# and a refusal returned as data naming its guard instead of an exception the model never sees.
import asyncio

from centinela_tools.server import answer, build_server, day_of
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of

from support import fixture_entries

SOURCES = load_sources()


def never(role):
    raise AssertionError("no connection")


def server():
    return build_server(SOURCES, catalogue_of(fixture_entries(), SOURCES), Settings(), never)


def test_the_server_exposes_exactly_the_four_tools():
    tools = asyncio.run(server().list_tools())
    assert {tool.name for tool in tools} == {"kpi_validar", "kpi_dry_run", "kpi_consultar", "kpi_catalogo"}


def test_no_tool_takes_sql():
    for tool in asyncio.run(server().list_tools()):
        assert not {"sql", "consulta", "query"} & set(tool.inputSchema.get("properties", {})), tool.name


def test_a_refusal_is_returned_as_data_with_its_guard():
    def refuse():
        raise Refused("hash", "tampered")

    assert answer(refuse) == {"rechazado": {"guarda": "hash", "detalle": "tampered"}}


def test_a_bad_day_is_refused_by_the_language_guard():
    assert answer(lambda: day_of("ayer"))["rechazado"]["guarda"] == "lenguaje"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_server.py -q`
Expected: `ModuleNotFoundError: No module named 'centinela_tools.server'`.

- [ ] **Step 3: Write `server.py`**

```python
import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping

import psycopg
from mcp.server.fastmcp import FastMCP

from . import tools
from .paths import METRICAS
from .refusal import Refused
from .settings import Settings
from .sources import Sources, load_sources


def answer(call: Callable[[], Any]) -> Any:
    try:
        return call()
    except Refused as error:
        return {"rechazado": {"guarda": error.guard, "detalle": error.detail}}


def day_of(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise Refused("lenguaje", f"dia: {text!r} is not a date YYYY-MM-DD") from error


def build_server(sources: Sources, catalogue: tools.Catalogue, settings: Settings, connect: tools.Connect) -> FastMCP:
    server = FastMCP("centinela-kernel")

    @server.tool(description="Checks a kernel: block against the language, fuentes.yaml, the clock rules and the planner's cost on dia; returns its compiled SQL, hash and columns, or the guard that refused it.")
    def kpi_validar(bloque: dict, dia: str) -> dict:
        return answer(lambda: tools.kpi_validar(bloque, day_of(dia), sources, connect, settings))

    @server.tool(description="Validates a kernel: block and runs it read-only on dia under the timeout; returns the first rows, the row count and the time, or the guard that refused it.")
    def kpi_dry_run(bloque: dict, dia: str) -> dict:
        return answer(lambda: tools.kpi_dry_run(bloque, day_of(dia), sources, connect, settings))

    @server.tool(description="Runs a KPI of the client's catalogue by id on dia; returns its rows with the query that produced them.")
    def kpi_consultar(kpi: str, dia: str) -> dict:
        return answer(lambda: tools.kpi_consultar(kpi, day_of(dia), catalogue, connect, settings))

    @server.tool(description="Lists the client's KPIs, base and approved, with their ISO 22400-2 fields, entity, columns and whether each is descriptive.")
    def kpi_catalogo() -> dict:
        return {"kpis": tools.kpi_catalogo(catalogue)}

    return server


def connector(env: Mapping[str, str]) -> tools.Connect:
    dsns = {"lector": env["CENTINELA_LECTOR_DSN"], "kernel": env["CENTINELA_KERNEL_DSN"]}
    return lambda role: psycopg.connect(dsns[role], autocommit=True)


def main(env: Mapping[str, str] = os.environ) -> None:
    sources = load_sources()
    path = env.get("CENTINELA_KPIS_APROBADOS")
    approved = json.loads(Path(path).read_text()) if path else []
    catalogue = tools.catalogue_of(tools.load_entries(METRICAS), sources, approved)
    build_server(sources, catalogue, Settings.from_env(env), connector(env)).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run every test**

Run: `uv run pytest -q`
Expected: all pass. If `list_tools` or the `description=` argument has another shape in the installed `mcp`, read `uv run python -c "import mcp.server.fastmcp as m, inspect; print(inspect.signature(m.FastMCP.tool))"`. Adapt the server, never the test's four names.

- [ ] **Step 5: Smoke-test the stdio server**

Run: `CENTINELA_LECTOR_DSN=postgresql://centinela_lector:centinela_lector@localhost:55432/centinela CENTINELA_KERNEL_DSN=postgresql://centinela_kernel:centinela_kernel@localhost:55432/centinela timeout 3 uv run python -m centinela_tools.server < /dev/null; echo $?`
Expected: exit code 0 or 124, and no traceback.

- [ ] **Step 6: Ask the user, then commit**

```bash
git add packages/tools
git commit -q -F - <<'MSG'
Serve the kernel's four tools over MCP stdio, taking a block or an id and never SQL from a model

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 8: The level pages

**Files:**
- Modify: `data/AGENTS.md`, `packages/tools/AGENTS.md`, `AGENTS.md` (root), `GENERATED.md`, `DOUBTS.md`

**Interfaces:**
- Consumes: every decision above.
- Produces: the headings `data/AGENTS.md` § "The kernel's language" and `packages/tools/AGENTS.md` § "The KPI kernel", which Task 9's `Draws:` captions name.

- [ ] **Step 1: `data/AGENTS.md`, "Why each file exists"**

After the `metricas.yaml` row, add:

| Path | Why it exists |
|---|---|
| `metricas.yaml`, a `kernel:` block | the definition the kernel compiles for a base metric, in the language of `kernel/lenguaje.schema.json`. An entry with a block also carries the ISO 22400-2 fields `unidad`, `rango`, `tendencia`, `temporalidad` and `audiencia`, and keeps `formula` as the readable one |
| `kernel/lenguaje.schema.json` | the kernel's language as a JSON Schema: the closed keys of a `kernel:` block with their bounds, and the ISO 22400-2 fields under `$defs/ficha` |
| `kernel/fuentes.yaml` | what the kernel may read: each table's key, its readable columns with their type, the role of each date column, its `fuga` columns with the values known when a row is created, and the columns it excludes with the reason; and each source's joins, closings and dimensions |
| `sql/05_kpis.generated.sql` | written by the kernel's generator ([`../GENERATED.md`](<../GENERATED.md>)): the roles `centinela_lector` and `centinela_kernel` with their grants, `fecha_corte()` made readable through the views, and one function `centinela.k_<metric>(dia date)` per metric with a `kernel:` block |

- [ ] **Step 2: `data/AGENTS.md`, "Rules of this level"**

Replace the first rule's second sentence. It becomes: "A base metric is an entry in `metricas.yaml` whose `kernel:` block compiles to `centinela.k_<metric>(dia)` in `sql/05_kpis.generated.sql`; the `v_*` views are the kit's reference and the cause views. An approved metric lives in `apps/api`'s catalogue and never in this schema." Keep the rest of the rule.

Replace the rule "Tools connect as a read-only database user granted only the `v_*` views." with: "**Tools connect as `centinela_lector`, granted `SELECT` on the `v_*` views and `EXECUTE` on `centinela.k_*`, and the kernel's own runs as `centinela_kernel`, granted `SELECT` column by column on the readable columns of `kernel/fuentes.yaml`.** No role a tool holds may write, not even a temporary table, which is the gate of the law that no agent changes a database. The `k_` functions and `fecha_corte()` are `SECURITY DEFINER`, owned by `centinela_kernel`, so the reader runs them without reading a table and they read no column the kernel cannot. Both roles' passwords are their names, like the compose's, because the database holds only the synthetic dataset. Write access belongs to the API's own tables, never to this schema."

- [ ] **Step 3: `data/AGENTS.md`, "Setting up the database"**

After the `04` line of the block, add `psql -d centinela -f sql/05_kpis.generated.sql`. Replace the last line with
`psql "postgresql://centinela_lector:centinela_lector@localhost/centinela" -c "SELECT * FROM centinela.v_cobertura_inventario ORDER BY cobertura_dias LIMIT 5;"`, so the check runs as the reader. After the block, add: "`05_kpis.generated.sql` creates the roles, which belong to the cluster, so it runs again unchanged on a second database of the same cluster."

- [ ] **Step 4: `data/AGENTS.md`, "The simulated clock"**

Add a paragraph at the end of the section: "**A kernel KPI takes the simulated day as its argument, so the leaks this section lists do not reach it.** The compiler bounds every event date it reaches by `dia`. It reads a closing date as empty after `dia`. It measures a weekly or monthly baseline only over complete periods. It joins a payment only when `fecha_pago <= dia`. It refuses a KPI for which it cannot do that ([the kernel's language](#the-kernels-language))."

- [ ] **Step 5: `data/AGENTS.md`, new section `## The kernel's language` after "The simulated clock"**

> A `kernel:` block holds one KPI, and every key comes from this closed list; any other key is refused. `kernel/lenguaje.schema.json` holds the keys and the bounds; the compiler in [`../packages/tools/AGENTS.md`](<../packages/tools/AGENTS.md>) checks the rest against `kernel/fuentes.yaml`.
>
> | Key | Holds | Bound |
> |---|---|---|
> | `fuente` | one source of `kernel/fuentes.yaml`: a table of `sql/01_esquema.sql`, never a `v_*` view, because several views compute "today" from `fecha_corte()` | a closed list |
> | `unir` | names of the source's joins | at most three, each after the one it joins from |
> | `abierto_al_dia` | `desde`, an event date, and `hasta`, a closing date or a closing the source declares: the rows open on `dia` | one time frame per KPI |
> | `ventana` | an event date and a number of days back from `dia` | at most 365 days; one time frame per KPI |
> | `filtro` | a column, an operator from `=`, `!=`, `<`, `<=`, `>`, `>=`, `en`, and a literal of the column's type | at most five; an `en` list of at most 20; no `%` in a text literal |
> | `agrupar` | dimensions the source declares, or `{columna, por}` with `semana` or `mes` over an event or term date; it is the KPI's entity, one row per entity | one to three |
> | `medida` | `sum`, `avg`, `count`, `min`, `max` or `mediana` over a column, or over one expression of `+ - * /` over columns | expression depth two |
> | `razon` | a `medida` over another `medida`, in place of `medida` | one |
> | `linea_base` | an event date, `semana` or `mes`, N, and `delta` or `delta_pct`: the last complete period before `dia` against the mean of the N before it | N at most 12; one time frame per KPI |
> | `salida` | the names of the output columns: `valor`, plus `base` and `delta` with a `linea_base` | each unique, never `dia` or `periodo` |
>
> **Every date column has a role**, because `dia` bounds each kind differently:
> - `evento`: the row exists from that day, and the compiler adds `<= dia`.
> - `plazo`: a promised date such as `fecha_vencimiento`, read as is.
> - `cierre`: an event that closes the row, such as `fecha_recibida`, read as empty after `dia`.
>
> A source with no date of its own names the join that dates it in `fechada_por`, and a KPI that omits that join is refused.
>
> **A join is many-to-one**, so it never multiplies a row. It goes along a foreign key of `sql/01_esquema.sql`, or onto the key of a `ref_*` table, which has none, and compiles to `LEFT JOIN`. A child such as a payment reaches a KPI only as a **closing** in `abierto_al_dia.hasta`: an invoice is open while no payment exists up to `dia`, because the data holds one full payment per invoice.
>
> **A `fuga` column holds the end of the dataset.** It is never a dimension or an operand. A filter reads it only with `=`, `!=` or `en` on the values known when a row is created, `Cancelado` for `pedidos.estado` and none for `ordenes_compra.estado`. The generator decides a cancellation when it creates the order, while `Pendiente de despacho` is the state at the end. A column holding a person's name, such as `vendedores.nombre`, is excluded, because personal data is masked before an agent sees it.
>
> **A KPI with no `fuente_umbral` is descriptive**: evidence for `Analista` and `Estratega`, and an operand no `detectar` node may compare, because no threshold exists that a document does not state. A measure the language cannot express is a defect of the language, fixed by a new primitive with its bound, never by a hand-written function. `uv run pytest tests/test_sources.py` in `packages/tools` checks every table, column, key and join of `fuentes.yaml` against `sql/01_esquema.sql`.

- [ ] **Step 6: `packages/tools/AGENTS.md`**

Intro: replace "It holds no code yet; this page states the decisions the code is written against." with "It holds the KPI kernel as code; the other servers hold none yet, and this page states the decisions all of them are written against."

Add after the intro:

> ## Why each file exists
>
> | Path | Why it exists |
> |---|---|
> | `centinela_tools/sources.py`, `language.py` | load `data/kernel/fuentes.yaml` and check a block against `data/kernel/lenguaje.schema.json` |
> | `centinela_tools/compiler.py` | a `kernel:` block → SQL composed with `psycopg.sql`, the `k_` function, the hash |
> | `centinela_tools/tools.py` | the catalogue and the kernel's four tools |
> | `centinela_tools/generate.py` | writes `data/sql/05_kpis.generated.sql` |
> | `centinela_tools/server.py` | the kernel's MCP server |
> | `tests/` | one planted violation per bound and guard; the tests marked `db` need the scratch database |
> | `pyproject.toml`, `uv.lock` | the package and its pinned dependencies; `uv.lock` is written by uv ([`../../GENERATED.md`](<../../GENERATED.md>)) |
>
> ## Commands
>
> Run from this directory, with [uv](https://docs.astral.sh/uv/):
>
> | Command | What it does |
> |---|---|
> | `uv sync` | installs the package and its dependencies into `.venv` |
> | `uv run pytest` | runs every test; those marked `db` are skipped, with the reason, unless `CENTINELA_TEST_DSN` is set |
> | `uv run python -m centinela_tools.generate` | writes `data/sql/05_kpis.generated.sql`; with a metric that carries `kernel:`, `CENTINELA_DSN` names a database loaded with `data/sql/01` to `04`, for the planner's cost |
> | `uv run python -m centinela_tools.server` | serves the kernel over stdio, with `CENTINELA_LECTOR_DSN`, `CENTINELA_KERNEL_DSN` and, optionally, `CENTINELA_KPIS_APROBADOS` |
>
> The scratch database for the `db` tests is a disposable container on port 55432, never the compose's volume:
>
> *(the `docker run` block of Task 5 Step 6, then)* `export CENTINELA_TEST_DSN=postgresql://centinela:centinela@localhost:55432/centinela`, and `docker stop centinela-kernel-test` removes it.

In "Decisions", in the list of servers, add a first item: "**the KPI kernel**, four read-only tools over the closed language of [`../../data/AGENTS.md`](<../../data/AGENTS.md>) ([below](#the-kpi-kernel)); **the kernel has no action: a KPI becomes active by `apps/api`'s record of an approval, never by a change to a database**;". Then add a decision: "**A server speaks stdio**, one process per concern. Which agent reaches which server, and how, is [`../agents/AGENTS.md`](<../agents/AGENTS.md>)'s."

Add at the end the section `## The KPI kernel`:

> The kernel is a **workbench with a closed language**: it compiles a `kernel:` block to SQL with `psycopg.sql` composition, never by interpolation, and refuses anything it cannot bound in cost or in time. No path, for a person or a model, takes free SQL: a tool receives a block or an id, so what cannot be written cannot be injected. `centinela_tools/compiler.py:compile_kpi(block, sources, day)` takes `dia` and applies it to every date column the KPI reaches, so a KPI is correct on any simulated day by construction.
>
> | Kind | Defined in | Reaches the database | Runs as |
> |---|---|---|---|
> | base | its entry of `data/metricas.yaml`, in a `kernel:` block | when a person sets the database up, as `centinela.k_<metric>(dia)` in `data/sql/05_kpis.generated.sql` | the function, called by `centinela_lector` |
> | approved | `apps/api`'s catalogue | never: nothing is created at runtime | its frozen compiled SQL, stored with its hash and compiler version at approval, run as stored text with `dia` as a parameter by `centinela_kernel` |
> | descriptive | either home, with no `fuente_umbral` | as its home says | evidence; no `detectar` node compares it |
>
> **What runs is what was approved.** `kpi_consultar` refuses an approved KPI whose stored SQL does not match its hash. A change to the compiler, which raises `COMPILER_VERSION`, never changes an approved KPI. It changes a base KPI only through the regenerated file, which a person reviews in the diff. An approved KPI that proves its worth is promoted by a person's pull request into `metricas.yaml`.
>
> Every refusal names its guard, from `centinela_tools/refusal.py:GUARDS`:
>
> | Guard | Refuses | Checked | Setting, default |
> |---|---|---|---|
> | `lenguaje` | a key, a bound or a type outside the language | at validation, before any SQL exists | |
> | `fuente` | a source, join, column or dimension `fuentes.yaml` does not grant, or a `fuga` read | at validation | |
> | `reloj` | a date `dia` cannot bound | at validation | |
> | `costo` | the planner's estimate (`EXPLAIN` on `dia`) over the cap | at validation and at generation | `CENTINELA_KERNEL_COSTO_MAX`, *(value and the kit views' measured costs from Task 6 Step 6)* |
> | `tiempo` | a run past `statement_timeout` | at dry run and on every call | `CENTINELA_KERNEL_TIMEOUT_MS`, 5000 |
> | `cardinalidad` | more groups than the cap | at dry run | `CENTINELA_KERNEL_GRUPOS_MAX`, 20000 |
> | `hash` | an approved KPI whose stored SQL changed | on every call | |
> | `catalogo` | an id in no catalogue | on every call | |
>
> The rows a dry run returns are capped by `CENTINELA_KERNEL_MUESTRA`, 20. The settings are sized to the machine, as Ollama's model is. Every run is a read-only transaction.
>
> | Tool | Who calls it | Does |
> |---|---|---|
> | `kpi_validar` | `Vigía`'s `proponer_kpi`, the generator, the tests | checks a block on `dia` against the language, `fuentes.yaml`, the clock rules and the planner's cost; returns the compiled SQL, its hash, the compiler version, the entity and the columns |
> | `kpi_dry_run` | `Vigía`'s `proponer_kpi`, the tests | validates a block and runs it as `centinela_kernel` on `dia` under the timeout; returns the first rows, the row count and the time |
> | `kpi_consultar` | the tree's nodes in code (`detectar`, `ejecutar.vigente`), `Analista`, `calcular_impacto` | runs a KPI by id on `dia`, base through its function as `centinela_lector`, approved through its stored SQL after the hash check; returns the rows with the query |
> | `kpi_catalogo` | every agent the tree gives the SQL tool | lists the client's KPIs, base and approved, with their ISO 22400-2 fields, entity, columns and whether each is descriptive |
>
> A refusal returns as `{"rechazado": {"guarda", "detalle"}}`, so the model reads which guard refused. The model names a KPI by id and never passes SQL. The orchestrator, which is code, writes the client's approved KPIs (id, stored SQL, hash, card, entity, columns) to the JSON file `CENTINELA_KPIS_APROBADOS` names, as `apps/api` hands them to it.

- [ ] **Step 7: Root `AGENTS.md`, `GENERATED.md`, `DOUBTS.md`**

- Root `AGENTS.md`: change "`apps/web` holds a scaffold and `packages/agents` holds the decision tree's validator and interpreter; the other parts hold no code yet." to "`apps/web` holds a scaffold, `packages/agents` holds the decision tree's validator and interpreter, and `packages/tools` holds the KPI kernel; the other parts hold no code yet." In "Commands", change "and `uv sync` in `packages/agents`, whose commands ..." to also name `packages/tools` and link [`packages/tools/AGENTS.md`](<./packages/tools/AGENTS.md>).
- `GENERATED.md`, "What writes today": add the row `| `uv run python -m centinela_tools.generate`, run in `packages/tools` | `data/sql/05_kpis.generated.sql`, from `data/kernel/fuentes.yaml`, `data/metricas.yaml` and the view names of `data/sql/03` and `04` | none needed: the name says so, and its banner names the command; `tests/test_generate.py` fails when the file differs from what the generator writes |`.
- `DOUBTS.md`, "The base tree reads KPI columns no kernel builds": replace "No part serves that catalogue: the only one is the tests'" with "`packages/tools` serves `kpi_catalogo`, but it lists only entries of `metricas.yaml` with a `kernel:` block, and none has one, so the only catalogue the tree is validated against is the tests'". Change "It is paid when the kernel builds every column below, `packages/tools` serves `kpi_catalogo`, and the startup validates against it." to "It is paid when every metric carries a `kernel:` block that builds every column below, and the startup validates against `kpi_catalogo`."

- [ ] **Step 8: Verify the links and the present tense**

Run the link check of `CLAUDE.md`, verification step 6. Expected: no output.
Run: `grep -n "will \|no code yet\|read-only database user granted only" data/AGENTS.md packages/tools/AGENTS.md AGENTS.md`
Expected: no stale sentence.

- [ ] **Step 9: Ask the user, then commit**

```bash
git add data/AGENTS.md packages/tools/AGENTS.md AGENTS.md GENERATED.md DOUBTS.md
git commit -q -F - <<'MSG'
Write the kernel's language into data's page and its tools, guards and roles into packages/tools, where the code they describe now lives

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

---

### Task 9: The guide chapter, and the checks only a person runs

**Files:**
- Modify: `docs/guide/chapters/kpi-kernel.md`, `docs/guide/chapters/status.md`

**Interfaces:**
- Consumes: the headings `data/AGENTS.md` § "The kernel's language" and `packages/tools/AGENTS.md` § "The KPI kernel".
- Produces: a chapter that owns only what no level page states.

- [ ] **Step 1: Shrink the chapter**

In `docs/guide/chapters/kpi-kernel.md`:
- Change the intro's last sentence to: "The language is [data](<../../../data/AGENTS.md>)'s, and the compiler, its guards and its tools are [packages/tools](<../../../packages/tools/AGENTS.md>)'s; this chapter draws them and owns the two parts still to be built."
- Change the top warning box to: `> **Decided, not implemented.** No metric of `metricas.yaml` carries a `kernel:` block yet, so `05_kpis.generated.sql` holds the roles and no function, and no agent calls the kernel's tools. The two sections below are what remains.`
- Replace the sections "A language and a compiler, never free SQL", "Three kinds of KPI", "The language" and "The guards, the roles and the law" with one section, `## Where the kernel is stated`. It holds two sentences linking `data/AGENTS.md` § The kernel's language and `packages/tools/AGENTS.md` § The KPI kernel, plus the law in one line: "No role an agent's tools hold can write, which makes the grants the gate of the law that no agent changes a database."
- In "The tools, and who consults the kernel at each stage", drop the tools table and keep the flowchart, the sentence about `Ejecutor` and the sentence about the model naming a KPI by id. Add under the diagram: `*Draws: `packages/tools/AGENTS.md` § The KPI kernel*`.
- Open "Rebuilding the current metrics" and "How a new KPI is born" each with `> **Decided, not implemented.**` plus one line saying what is missing.

- [ ] **Step 2: `status.md`**

In the "By part" table, change the `data` row's last cell to "the `kernel:` block of each current metric ([the KPI kernel](<./kpi-kernel.md>))" and the `packages/tools` row's to "the kernel KPIs that `calcular_impacto` and `Vigía` read".

- [ ] **Step 3: Build the guide without Docmost**

Run: `cd docs/guide && python publish.py --build-only "$(mktemp -d)"`
Expected: no `draws ... which that page lacks` problem. A missing heading means the caption or the heading is misspelled: fix the caption.

- [ ] **Step 4: Run the whole verification**

Run: `cd packages/tools && uv run pytest -q` with `CENTINELA_TEST_DSN` set, then `cd ../agents && uv run pytest -q`.
Expected: every test passes in both packages.
Run: the `CLAUDE.md` link check. Expected: no output.
Run: `git status --short`, against `GENERATED.md`. Expected: only the files of this task. `05_kpis.generated.sql` is unchanged, unless a source changed.

- [ ] **Step 5: Ask the user, then commit**

```bash
git add docs/guide/chapters/kpi-kernel.md docs/guide/chapters/status.md
git commit -q -F - <<'MSG'
Shrink the kernel chapter to links and its diagrams now that the level pages state the kernel

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GjWo81WCrA43HJXs7srRxV
MSG
```

- [ ] **Step 6: Hand the person-only checks to the user**

Ask the user to run these and report:

1. **The compose from scratch**: `cd data && docker compose down -v && docker compose up -d`, then the reader's query of `data/AGENTS.md` "Setting up the database". It proves that initdb applies `05` after `04` and that `centinela_lector` reads a view.
2. **pgAdmin**: connect as `centinela_lector` and check that no table of `centinela` opens and every `v_*` view does.
3. **The guide**: `python publish.py` in `docs/guide`, then read "The KPI kernel" and "What exists today" in Docmost. Check that the flowchart renders and that the links open their pages.
4. **An end-to-end read** of every page this plan touched, for present tense and for a fact stated in two places (`CLAUDE.md` verification 7).

Then `docker stop centinela-kernel-test`. The plan stays until the user confirms; deleting it is a separate commit, by `CLAUDE.md`'s rule.

---

## Self-review against the spec

| Spec requirement | Task |
|---|---|
| closed language, any other key refused | 3 |
| the language in `data`, the compiler and tools in `packages/tools` | 2, 3, 4 |
| a KPI is a function of `dia`; weekly baseline on complete weeks; payment only `<= dia` | 4, 6 |
| base kind in `05_kpis.generated.sql` with banner, `SECURITY DEFINER`, fixed `search_path` | 4, 5 |
| approved kind: stored SQL plus hash plus compiler version, run as text, hash checked | 4, 6 |
| ISO 22400-2 fields | 3 |
| descriptive KPI | 6, 8 |
| `fuentes.yaml` with `fuga`, readable columns, joins, schema test | 2 |
| roles and column grants generated from `fuentes.yaml`; no write | 5 |
| guards: bounds, `EXPLAIN` cost, timeout, cardinality, each named | 3, 4, 5, 6 |
| four tools; model never passes SQL; approved KPIs as run context | 6, 7 |
| pages of "Pages this spec changes" | 8, 9 |
| Acceptance: one refusal per bound, guard and clock rule | 3, 4, 6 |
| Acceptance: no public compiler function lets a string reach SQL outside composition | 4 (AST tests) |
| Acceptance: the reader cannot `SELECT` a table and can `EXECUTE` `k_*` | 5 |
| Acceptance: `centinela_kernel` cannot read an unlisted column or write | 5 |
| Acceptance: `kpi_consultar` refuses a hash mismatch | 6 |
