# packages/tools: the closed list of tools

This level holds the tools the agents call. **The list of tools is closed**: an agent can do
exactly what a tool here exposes and nothing else, which is what makes an acting agent safe to
buy. It holds the KPI kernel as code; the other tools hold none yet, and this page states the
decisions all of them are written against.

## Why each file exists

| Path | Why it exists |
|---|---|
| `centinela_tools/sources.py`, `language.py` | load `data/kernel/fuentes.yaml`, refusing an inconsistent one, and check a block or a card against `data/kernel/lenguaje.schema.json` |
| `centinela_tools/compiler.py` | a `kernel:` block → SQL composed with `psycopg.sql`, the `k_` function, the hash |
| `centinela_tools/tools.py` | the catalogue and the kernel's four tools |
| `centinela_tools/generate.py` | writes `data/sql/05_kpis.generated.sql` |
| `centinela_tools/kernel.py` | the kernel's contract: the JSON Schema of each of its four tools, and the one call that checks arguments against it and dispatches |
| `centinela_tools/refusal.py`, `settings.py`, `paths.py` | the closed list of guards, the settings read from the environment, and where the files of `data/` are |
| `tests/` | planted violations of every bound, rule of `fuentes.yaml` and guard; `tests/fixtures/metricas.yaml` holds the KPIs they compile; `tests/test_parity.py` checks every base KPI against its view and an as-of query; the tests marked `db` need the scratch database |
| `pyproject.toml`, `uv.lock` | the package and its pinned dependencies; `uv.lock` is written by uv ([`../../GENERATED.md`](../../GENERATED.md)) |

## Commands

Run from this directory, with [uv](https://docs.astral.sh/uv/):

| Command | What it does |
|---|---|
| `uv sync` | installs the package and its dependencies into `.venv` |
| `uv run pytest` | runs every test; those marked `db` are skipped, with the reason, unless `CENTINELA_TEST_DSN` is set |
| `uv run python -m centinela_tools.generate` | writes `data/sql/05_kpis.generated.sql`; with a metric that carries `kernel:`, `CENTINELA_DSN` names a database loaded with `data/sql/01` to `04`, for the planner's cost |

The scratch database for the `db` tests is a disposable container on port 55432, never the
compose's volume:

```bash
docker run -d --rm --name centinela-kernel-test -p 55432:5432 \
  -e POSTGRES_DB=centinela -e POSTGRES_USER=centinela -e POSTGRES_PASSWORD=centinela \
  -v "$PWD/../../data/sql/01_esquema.sql:/docker-entrypoint-initdb.d/01_esquema.sql:ro" \
  -v "$PWD/../../data/sql/02_carga.sql:/docker-entrypoint-initdb.d/02_carga.sql:ro" \
  -v "$PWD/../../data/sql/03_capa_semantica.sql:/docker-entrypoint-initdb.d/03_capa_semantica.sql:ro" \
  -v "$PWD/../../data/sql/04_vistas_causa.sql:/docker-entrypoint-initdb.d/04_vistas_causa.sql:ro" \
  -v "$PWD/../../data/csv:/csv:ro" postgres:16-alpine
export CENTINELA_TEST_DSN=postgresql://centinela:centinela@localhost:55432/centinela
```

The load takes a while after the container starts; the tests can run once
`docker exec centinela-kernel-test psql -U centinela -d centinela -h 127.0.0.1 -tAc 'SELECT count(*) FROM centinela.v_ventas'`
prints a number. The test session applies `data/sql/05_kpis.generated.sql`'s roles and grants
itself. `docker stop centinela-kernel-test` removes the container.

## Decisions

- **The KPI kernel is Python functions behind a JSON Schema contract, not a server**: four
  read-only tools over the closed language of [`../../data/AGENTS.md`](../../data/AGENTS.md)
  ([below](#the-kpi-kernel)). Most of its callers are code, the tree's nodes and
  `calcular_impacto`, which a process boundary would only slow; a model reaches it through native
  function calling, which takes the contract as it stands. What closes the list is the contract,
  exactly four tools and none taking SQL, not a transport. **The kernel has no action: a KPI
  becomes active by `apps/api`'s record of an approval, never by a change to a database.**
- **The other tools are MCP servers**, one per concern:
  - **read-only SQL** over the `v_*` views of the semantic layer
    ([`../../data/AGENTS.md`](../../data/AGENTS.md)), connected as `centinela_lector`;
  - **policy search** over [`../../data/policies/`](../../data/policies/), embedded in pgvector;
  - **the impact calculator**, `calcular_impacto`, which `Estratega` calls for every amount it proposes;
  - **actions**, each producing a draft or a sandbox effect: `email_draft`, `task`,
    `purchase_order_draft`, `price_change_draft`.
- **A server speaks stdio**, one process per concern. Which agent reaches which tool, and how, is
  [`../agents/AGENTS.md`](../agents/AGENTS.md)'s.
- **Every SQL tool takes the simulated day** and filters by it, because not every view does. The
  cause views of `data/sql/04_vistas_causa.sql` are read like any other view; `Analista` needs them
  because supplier costs, list prices and purchase orders reach no kit view.
- **Policies are embedded with `bge-m3` through Ollama**, because every model runs locally and the
  policies are in Spanish, which `bge-m3` reads well.
- **Personal data is masked in the SQL tool**, before a result reaches any agent: a seller is
  `vendedor_id`, never a name, because sellers are people and customers and suppliers are
  companies. `apps/web` resolves an id to a name for the person who reads it.

## The impact calculator

`calcular_impacto` takes a formula name, the alert's entity and the simulated day, runs
`kpi_consultar` on the KPIs below, and returns each figure with its query. The formula, not the
model, chooses every percentage and quantity. Every formula assumes volume holds, and returns that assumption.

| Formula | Returns | Computed as |
|---|---|---|
| `traslado_costo` | `price_increase_pct`, impact per month | the increase from `costo_anterior` to `costo_unitario` over `precio_lista`, the list price in force, all of `k_variacion_costo_pct`; times its `unidades_mes_prom`, the SKU's mean monthly units over the last 90 days |
| `precio_a_margen_minimo` | `price_increase_pct`, impact per month | the price change that takes the line's `margen_pct` to `margen_minimo_pct`, both of `k_margen_pct`; the margin gap times its `ventas_mes_prom`, the line's mean monthly `valor_neto` over the last 90 days |
| `cartera_vencida` | impact once | the customer's `saldo_vencido` in `k_saldo_vencido` |
| `ventas_protegidas` | `units`, impact once | `demanda_prom_30d` of `k_cobertura_dias` times the class minimum coverage of `OPE-POL-007 §2` minus its `existencia`; those units times its `precio_lista`, the list price in force |
| `descuento_recuperado` | impact per month | the seller's `sum(descuento_en_exceso)` over the rows of `k_descuento_en_exceso` whose `semana` falls in the last four weeks |
| `venta_bajo_costo` | impact per month | `-sum(margen_bruto)` of the SKU's rows of `k_margen_bruto_negativo` whose `fecha` falls in the last four weeks |
| `compra_recuperada` | impact per month | the customer's `pesos_en_riesgo` in `k_veces_intervalo_habitual`, its mean monthly `valor_neto` over the six months up to `ultima_compra` |

## Rules of this level

- **Every query is logged and returned with its result**, so the figure and the query that
  produced it travel together to the log and the screen. *No gate holds this.*
- **Retrieved text is data, never instructions.** Policy search returns passages as quoted content
  marked as such; a passage that reads like an order is reported, not obeyed.
- **Actions are idempotent**: the same approved action executed twice has one effect.
- **No tool writes to the dataset schema, and no action leaves draft or sandbox.**
- **Adding a tool widens what an agent can do**, so a new tool states, on this page, what it can
  touch and why the agents need it. Which agent is given which tool is
  [`../agents/AGENTS.md`](../agents/AGENTS.md).

## The KPI kernel

The kernel is a **workbench with a closed language**: it compiles a `kernel:` block to SQL with
`psycopg.sql` composition, never by interpolation, and refuses anything it cannot bound in cost or
in time. No path, for a person or a model, takes free SQL: a tool receives a block or an id, so
what cannot be written cannot be injected. `centinela_tools/compiler.py:compile_kpi(block, sources, day, thresholds)`
takes `dia` and applies it to every date column the KPI reaches, so a KPI is correct on any
simulated day by construction; `thresholds`, the entry's `umbrales`, answers an `umbral` operand.

| Kind | Defined in | Reaches the database | Runs as |
|---|---|---|---|
| base | its entry of `data/metricas.yaml`, in a `kernel:` block | when a person sets the database up, as `centinela.k_<metric>(dia)` in `data/sql/05_kpis.generated.sql` | the function, called by `centinela_lector` |
| approved | `apps/api`'s catalogue | never: nothing is created at runtime | its frozen compiled SQL, stored with its hash and compiler version at approval, run as stored text with `dia` as a parameter by `centinela_kernel` |
| descriptive | either home, with no `fuente_umbral` | as its home says | evidence; no `detectar` node compares it |

**What runs is what was approved.** `kpi_consultar` refuses an approved KPI whose stored SQL does
not match its hash. A change to the compiler, which raises
`centinela_tools/compiler.py:COMPILER_VERSION`, never changes an approved KPI. It changes a base KPI
only through the regenerated file, which a person reviews in the diff. An approved KPI that proves
its worth is promoted by a person's pull request into `metricas.yaml`.

Every refusal names its guard, from `centinela_tools/refusal.py:GUARDS`:

| Guard | Refuses | Checked | Setting, default |
|---|---|---|---|
| `lenguaje` | a key, a bound or a type outside the language, a KPI id or a `dia` out of form | at validation, before any SQL exists | |
| `fuente` | a source, join, column or dimension `fuentes.yaml` does not grant, or a `fuga` read | at validation | |
| `reloj` | a date `dia` cannot bound, or a source without the join that dates it | at validation | |
| `costo` | the planner's estimate (`EXPLAIN` on `dia`) over the cap | at validation and at generation | `CENTINELA_KERNEL_COSTO_MAX`, 1000000 |
| `tiempo` | a run past `statement_timeout` | on every call that reaches the database | `CENTINELA_KERNEL_TIMEOUT_MS`, 5000 |
| `cardinalidad` | more groups than the cap | at dry run | `CENTINELA_KERNEL_GRUPOS_MAX`, 20000 |
| `hash` | an approved KPI whose stored SQL changed | on every call | |
| `catalogo` | an id in no catalogue | on every call | |

**The cost cap is a measurement.** This command, run from this directory against a database loaded
with the official dataset, prints the planner's total cost on `fecha_corte()` of three of the kit's
views and of every base KPI of `data/metricas.yaml`:

```bash
CENTINELA_DSN=postgresql://centinela:centinela@localhost:55432/centinela uv run python -c '
import os
from psycopg import sql
from centinela_tools.compiler import compile_kpi
from centinela_tools.generate import database_cost
from centinela_tools.paths import METRICAS
from centinela_tools.sources import load_sources
from centinela_tools.tools import load_entries
cost = database_cost(os.environ["CENTINELA_DSN"])
for view in ("v_cartera_cliente", "v_cobertura_inventario", "v_actividad_cliente"):
    print(view, round(cost(sql.SQL("SELECT * FROM {}").format(sql.Identifier("centinela", view)))))
for metric, entry in load_entries(METRICAS).items():
    print(metric, round(cost(compile_kpi(entry["kernel"], load_sources(), thresholds=entry.get("umbrales")).query)))
'
```

The default of 1000000 is well over ten times `v_cartera_cliente`'s, the costliest of the three
views, and leaves room above the costliest base KPI, a baseline. The rows a dry run returns are
capped by `CENTINELA_KERNEL_MUESTRA`, 20. The settings are sized to the machine, as Ollama's model is. Every
run is a transaction opened `READ ONLY` with its `statement_timeout`,
`centinela_tools/tools.py:guarded(conn, settings)`, inside the roles of
[`../../data/AGENTS.md`](../../data/AGENTS.md).

| Tool | Who calls it | Does |
|---|---|---|
| `kpi_validar` | `Vigía`'s `proponer_kpi`, the tests | checks a block on `dia` against the language, `fuentes.yaml`, the clock rules and the planner's cost; returns the compiled SQL, its hash, the compiler version, the entity, the columns and the cost |
| `kpi_dry_run` | `Vigía`'s `proponer_kpi`, the tests | validates a block and runs it as `centinela_kernel` on `dia` under the timeout; returns what `kpi_validar` returns, the first rows, the row count and the time in milliseconds, wall time including opening the connection |
| `kpi_consultar` | the tree's nodes in code (`detectar`, `ejecutar.vigente`), `Analista`, `calcular_impacto` | runs a KPI by id on `dia`, base through its function as `centinela_lector`, approved through its stored SQL after the hash check as `centinela_kernel`; returns the rows with the query |
| `kpi_catalogo` | every agent the tree gives the SQL tool | lists the client's KPIs, base and approved, with their card, entity, columns and whether each is descriptive |

The generator does not call `kpi_validar`: it compiles each block and applies the `costo` guard
itself, against the database `CENTINELA_DSN` names, on its `fecha_corte()`.

A refusal returns as `{"rechazado": {"guarda", "detalle"}}`, so the model reads which guard
refused. A database error that is no guard, such as an approved KPI whose stored text writes,
surfaces as a tool error. The model names a KPI by id and never passes SQL.
`centinela_tools/kernel.py:Kernel.call(name, arguments)` checks the arguments against the tool's
schema in `centinela_tools/kernel.py:CONTRACT` before it runs, so arguments out of contract return
as a `lenguaje` refusal, and a name outside the contract is an error.
`centinela_tools/kernel.py:kernel_from_env(env)` builds the catalogue, from the entries of `metricas.yaml` with a `kernel:` block and from the
JSON file `CENTINELA_KPIS_APROBADOS` names, so a base entry the language refuses stops it, and so
does an approved id that repeats or that a base KPI holds. The
orchestrator, which is code, writes that file as `apps/api` hands it the client's approved KPIs,
one record each with `id`, `ficha`, `descriptivo`, `entidad`, `columnas`, `sql`, `hash` and
`version_compilador`.
