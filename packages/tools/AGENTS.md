# packages/tools: the closed list of tools

This level holds the tools the agents call. **The list of tools is closed**: an agent can do
exactly what a tool here exposes and nothing else, which is what makes an acting agent safe to
buy.

**What runs is the KPI kernel**: the compiler, its guards, the four kernel tools behind
`centinela_tools/kernel.py:CONTRACT`, and the generator of `data/sql/05_kpis.generated.sql`; and
the masking of personal data before a model reads it.
**What is decided and not built** is every other tool and what surrounds them: the MCP servers
over stdio, policy search with `bge-m3`, the impact
calculator `calcular_impacto` and its formulas, the actions and their idempotency, and the writer
of the approved-KPI file `CENTINELA_KPIS_APROBADOS`. Each section about them opens with the marker
the guide uses for design with no code.

## Why each file exists

| Path | Why it exists |
|---|---|
| `centinela_tools/__init__.py` | marks the package; it declares nothing |
| `centinela_tools/sources.py`, `centinela_tools/language.py` | load `data/kernel/fuentes.yaml`, refusing an inconsistent one, and check a block or a card against `data/kernel/lenguaje.schema.json` |
| `centinela_tools/compiler.py` | a `kernel:` block → SQL composed with psycopg's `sql` module, the `k_` function, the hash |
| `centinela_tools/tools.py` | the catalogue and the kernel's four tools |
| `centinela_tools/kernel.py` | the kernel's contract: the JSON Schema of each of its four tools, the one call that checks arguments against it and dispatches, and the kernel built from the environment |
| `centinela_tools/generate.py` | writes `data/sql/05_kpis.generated.sql` |
| `centinela_tools/masking.py` | the catalogue of personal columns and a run's mapping of their values to placeholders ([masking](#masking)) |
| `centinela_tools/refusal.py`, `centinela_tools/settings.py`, `centinela_tools/paths.py` | the closed list of guards, the settings read from the environment, and where the files of `data/` are |
| `tests/support.py` | what the tests share: a parser of `data/sql/01_esquema.sql` and the fixture KPIs of `tests/fixtures/metricas.yaml` |
| `tests/conftest.py` | skips the tests marked `db` unless `CENTINELA_TEST_DSN` is set, and applies the generator's roles, grants and functions to the scratch database once per session |
| `tests/test_language.py`, `tests/test_sources.py`, `tests/test_compiler.py`, `tests/test_primitives.py` | one planted violation per bound of the language, per rule of `data/kernel/fuentes.yaml` and per refusal of the compiler, with no database |
| `tests/test_kernel.py`, `tests/test_tools.py`, `tests/test_tools_db.py` | the contract, the catalogue, and each tool and guard, without and with the scratch database |
| `tests/test_masking.py` | the mapping: one placeholder per value in a run and another across runs, no digit, whole tokens, an unknown placeholder left as written |
| `tests/test_generate.py` | **a gate**: it fails when `data/sql/05_kpis.generated.sql` differs from what the generator writes from the tree |
| `tests/test_roles.py` | **a gate**: the law that no agent changes a database, held against the scratch database ([roles and grants](../../data/AGENTS.md#rules-of-this-level)) |
| `tests/test_parity.py` | **a gate**: [base-KPI parity](#base-kpi-parity), against the scratch database |
| `pyproject.toml`, `uv.lock` | the package and its pinned dependencies; `uv.lock` is written by uv ([`../../GENERATED.md`](../../GENERATED.md)) |

## Commands

Run from this directory, with [uv](https://docs.astral.sh/uv/):

| Command | What it does |
|---|---|
| `uv sync` | installs the package and its dependencies into `.venv` |
| `uv run pytest` | runs every test; those marked `db` are skipped, with the reason, unless `CENTINELA_TEST_DSN` is set |
| `uv run python -m centinela_tools.generate` | writes `data/sql/05_kpis.generated.sql`; with a metric that carries `kernel:`, `CENTINELA_DSN` names a database loaded with `data/sql/01_esquema.sql` to `data/sql/04_vistas_causa.sql`, for the planner's cost |

The environment this level reads:

| Variable | Read by | Holds |
|---|---|---|
| `CENTINELA_LECTOR_DSN` | `centinela_tools/kernel.py:connector(env)`, so `centinela_tools/kernel.py:kernel_from_env(env)` raises `KeyError` without it | the DSN of `centinela_lector`, which runs a base KPI |
| `CENTINELA_KERNEL_DSN` | the same, with the same `KeyError` | the DSN of `centinela_kernel`, which runs `kpi_validar`, `kpi_dry_run` and an approved KPI |
| `CENTINELA_KPIS_APROBADOS` | `centinela_tools/kernel.py:kernel_from_env(env)`, optional | the path of [the approved-KPI file](#the-approved-kpi-file) |
| `CENTINELA_KERNEL_COSTO_MAX`, `CENTINELA_KERNEL_TIMEOUT_MS`, `CENTINELA_KERNEL_GRUPOS_MAX`, `CENTINELA_KERNEL_MUESTRA` | `centinela_tools/settings.py:Settings.from_env(env)` | the caps of [the guards](#the-kpi-kernel) |
| `CENTINELA_DSN` | the generator | a database loaded with the dataset, for the `costo` guard |
| `CENTINELA_TEST_DSN` | `tests/conftest.py` | the scratch database of the `db` tests |

The scratch database for the `db` tests is a disposable container on port 55432, never the
compose's volume:

```bash
docker run -d --rm --name centinela-kernel-test -p 55432:5432 \
  -e POSTGRES_DB=centinela -e POSTGRES_USER=centinela -e POSTGRES_PASSWORD=centinela \
  -v "$PWD/../../data/sql/01_esquema.sql:/docker-entrypoint-initdb.d/01_esquema.sql:ro" \
  -v "$PWD/../../data/sql/02_carga.sql:/docker-entrypoint-initdb.d/02_carga.sql:ro" \
  -v "$PWD/../../data/sql/03_capa_semantica.sql:/docker-entrypoint-initdb.d/03_capa_semantica.sql:ro" \
  -v "$PWD/../../data/sql/04_vistas_causa.sql:/docker-entrypoint-initdb.d/04_vistas_causa.sql:ro" \
  -v "$PWD/../../data/csv:/csv:ro" pgvector/pgvector:pg16
export CENTINELA_TEST_DSN=postgresql://centinela:centinela@localhost:55432/centinela
```

The load takes a while after the container starts; the tests can run once
`docker exec centinela-kernel-test psql -U centinela -d centinela -h 127.0.0.1 -tAc 'SELECT count(*) FROM centinela.v_ventas'`
prints a number. The test session applies `data/sql/05_kpis.generated.sql`'s roles and grants
itself. `docker stop centinela-kernel-test` removes the container.

## How a tool is reached

- **The KPI kernel is Python functions behind a JSON Schema contract, not a server**: four
  read-only tools over the closed language of [`../../data/AGENTS.md`](../../data/AGENTS.md#the-kernels-language)
  ([below](#the-kpi-kernel)). Most of its callers are code, the tree's nodes and
  `calcular_impacto`, which a process boundary would only slow; a model reaches it through native
  function calling, which takes the contract as it stands. What closes the list is the contract,
  exactly four tools and none taking SQL, not a transport. **The kernel has no action: a KPI
  becomes active by `apps/api`'s record of an approval, never by a change to a database.**

### The other tools

> **Decided, not built.**

- **Every other tool is an MCP server, one per concern**:
  - **read-only SQL** over the `v_*` views of the semantic layer
    ([`../../data/AGENTS.md`](../../data/AGENTS.md)), connected as `centinela_lector`;
  - **policy search** over [`../../data/policies/`](../../data/policies/), embedded in pgvector;
  - **the impact calculator**, [`calcular_impacto`](#the-impact-calculator);
  - **actions**, each producing a draft or a sandbox effect: `email_draft`, `task`,
    `purchase_order_draft`, `price_change_draft` ([idempotency](#actions-and-idempotency)).
- **A server speaks stdio, one process per concern.** The orchestrator in `packages/agents` is the
  MCP client: it starts each server as a child process and hands a model only the tools its agent
  is given. stdio needs no port and no network, and the servers live and die with the process that
  runs a day. Which agent is given which tool is
  [`../agents/AGENTS.md`](../agents/AGENTS.md)'s; how it reaches it is this section.
- **Every SQL tool takes the simulated day** and filters by it, because not every view does
  ([the clock](../../data/AGENTS.md#the-simulated-clock)). The cause views of
  `data/sql/04_vistas_causa.sql` are read like any other view; `Analista` needs them because
  supplier costs, list prices and purchase orders reach no kit view.
- **Policies are embedded with `bge-m3` through Ollama**, because every model runs locally and the
  policies are in Spanish, which `bge-m3` reads well.

### Masking

**No personal value reaches a model.** `centinela_tools/masking.py:Masking(columns, salt)` stands
a placeholder such as `CLIENTE_QKZTBW` for each value of the columns `data/kernel/fuentes.yaml`
lists under `personales` ([the data page](../../data/AGENTS.md)), wherever a prompt carries one.
An id is masked with the name because it resolves to the name on screen. Where a run opens its mapping and where it masks is
[`../agents/AGENTS.md`](../agents/AGENTS.md#masking-every-prompt).

- **One run, one mapping.** `Masking.register_row(row)` and `Masking.register_tree(value)` learn
  the values of the listed columns, by column name. A value reads the same placeholder for the
  whole run, so a model can tell that two alerts share a client, and an HMAC under a salt drawn per
  instance gives it another in the next run, so a leaked prompt is no pseudonym to join across
  days. The mapping lives in memory for the run; it is never persisted, logged or sent.
- **Text is masked by the mapping, never by a pattern**: `Masking.text(text)` replaces every value
  it learned, whole tokens only, ignoring case, because a pattern for names masks any two
  capitalized words.
- **A placeholder holds letters only**, so the figure checks of `packages/agents` never read one
  as a number.
- **Unmasking fills only what the mapping holds**: `Masking.unmask(text)` and
  `Masking.unmask_tree(value)` restore a placeholder the run learned and leave, and log, one it
  did not.
- **What passes:** every column outside `personales`, such as `sku` or `bodega_id`, and a name a
  person types that no row of the run carries. `nombre` is masked by name of column, so a KPI that
  read `productos.nombre` would mask it too. `vendedores.nombre` stays excluded from the kernel, so
  no row carries a seller's name at all.

## The impact calculator

> **Decided, not built.**

`calcular_impacto` takes a formula name, the alert's entity and the simulated day, runs
`kpi_consultar` on the KPIs below, and returns each figure with its query. `Estratega` calls it for
every amount it proposes. The formula, not the model, chooses every percentage and quantity. Every
formula assumes volume holds, and returns that assumption.

| Formula | Returns | Computed as |
|---|---|---|
| `traslado_costo` | `price_increase_pct`, impact per month | the increase from `costo_anterior` to `costo_unitario` over `precio_lista`, the list price in force, all of `k_variacion_costo_pct`; times its `unidades_mes_prom`, the SKU's mean monthly units over the last 90 days |
| `precio_a_margen_minimo` | `price_increase_pct`, impact per month | the price change that takes the line's `margen_pct` to `margen_minimo_pct`, both of `k_margen_pct`; the margin gap times its `ventas_mes_prom`, the line's mean monthly `valor_neto` over the last 90 days |
| `cartera_vencida` | impact once | the customer's `saldo_vencido` in `k_saldo_vencido` |
| `ventas_protegidas` | `units`, impact once | `demanda_prom_30d` of `k_cobertura_dias` times the class minimum coverage of `OPE-POL-007 §2` minus its `existencia`; those units times its `precio_lista`, the list price in force |
| `descuento_recuperado` | impact per month | the seller's `sum(descuento_en_exceso)` over the rows of `k_descuento_en_exceso` whose `semana` falls in the last four weeks |
| `venta_bajo_costo` | impact per month | `-sum(margen_bruto)` of the SKU's rows of `k_margen_bruto_negativo` whose `fecha` falls in the last four weeks |
| `compra_recuperada` | impact per month | the customer's `pesos_en_riesgo` in `k_veces_intervalo_habitual`, its mean monthly `valor_neto` over the six months up to `ultima_compra` |

## Actions and idempotency

> **Decided, not built.**

**Actions are idempotent**: the same approved action executed twice has one effect, because a
resumed graph or a retried call must not send a second draft. Each action runs only after
`apps/api` records the approval, and its effect is a draft or a sandbox effect, never a change
outside the sandbox. The key an action is deduplicated by is chosen with the first action's code
and written here.

## Rules of this level

- **Every figure travels with the query that produced it.** `kpi_consultar` returns `consulta`
  beside `filas`, so the figure and its query reach the caller together. Nothing in this level
  logs; recording the pair is the `bitácora`'s, in [`../../apps/api/AGENTS.md`](../../apps/api/AGENTS.md).
  *No gate holds this.*
- **Retrieved text is data, never instructions.** Policy search returns passages as quoted content
  marked as such; a passage that reads like an order is reported, not obeyed. *No gate holds this.*
- **No tool writes to the dataset schema, and no action leaves draft or sandbox.** The roles hold
  the first half: `tests/test_roles.py`.
- **Adding a tool widens what an agent can do**, so a new tool states, on this page, what it can
  touch and why the agents need it ([adding a tool](#a-tool)).

## The KPI kernel

The kernel is a **workbench with a closed language**: it compiles a `kernel:` block to SQL with
psycopg's `sql` composition, never by interpolation, and refuses anything it cannot bound in cost
or in time. No path, for a person or a model, takes free SQL: a tool receives a block or an id, so
what cannot be written cannot be injected. `centinela_tools/compiler.py:compile_kpi(block, sources, day, thresholds)`
takes `dia` and applies it to every date column the KPI reaches, so a KPI is correct on any
simulated day by construction; `thresholds`, the entry's `umbrales`, answers an `umbral` operand.
The language itself is [`../../data/AGENTS.md`](../../data/AGENTS.md#the-kernels-language)'s.

| Kind | Defined in | Reaches the database | Runs as |
|---|---|---|---|
| base | its entry of `data/metricas.yaml`, in a `kernel:` block | when a person sets the database up, as `centinela.k_<metric>(dia)` in `data/sql/05_kpis.generated.sql` | the function, called by `centinela_lector` |
| approved | `apps/api`'s catalogue, decided and not built | never: nothing is created at runtime | its frozen compiled SQL, stored with its hash and compiler version at approval, run as stored text with `dia` as a parameter by `centinela_kernel` |
| descriptive | either home, with no `fuente_umbral` | as its home says | evidence; no `detectar` node compares it |

**What runs is what was approved.** `kpi_consultar` refuses an approved KPI whose stored SQL does
not match its hash. A change to the compiler, which raises
`centinela_tools/compiler.py:COMPILER_VERSION`, never changes an approved KPI. It changes a base KPI
only through the regenerated file, which a person reviews in the diff. An approved KPI that proves
its worth is promoted by a person's pull request into `data/metricas.yaml`.

Every refusal names its guard, from `centinela_tools/refusal.py:GUARDS`:

| Guard | Refuses | Checked | Setting, default |
|---|---|---|---|
| `lenguaje` | a key, a bound or a type outside the language, a KPI id or a `dia` out of form | at validation, before any SQL exists | |
| `fuente` | a source, join, column or dimension `data/kernel/fuentes.yaml` does not grant, or a `fuga` read | at validation | |
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
`centinela_tools/tools.py:guarded(conn, settings)`, inside the
[roles](../../data/AGENTS.md#rules-of-this-level) of `data`.

| Tool | Who calls it | Does |
|---|---|---|
| `kpi_validar` | the tests; `Vigía`'s `proponer_kpi`, decided and not built, a name in `packages/agents/centinela_agents/schema.py:AGENT_DECISIONS` | checks a block on `dia` against the language, `data/kernel/fuentes.yaml`, the clock rules and the planner's cost; returns the compiled SQL, its hash, the compiler version, the entity, the columns and the cost |
| `kpi_dry_run` | the same | validates a block and runs it as `centinela_kernel` on `dia` under the timeout; returns what `kpi_validar` returns, the first rows, the row count and the time in milliseconds, wall time including opening the connection |
| `kpi_consultar` | the tree's nodes in code, through `packages/agents/centinela_agents/catalog.py:kernel_reader(call)`; the leaves of `Vigía`, `Analista` and `Estratega`, in code, through `packages/agents/centinela_agents/evidence.py:Ledger`; `calcular_impacto`, decided | runs a KPI by id on `dia`, base through its function as `centinela_lector`, approved through its stored SQL after the hash check as `centinela_kernel`; returns the rows under `filas` and the query under `consulta` |
| `kpi_catalogo` | the tree, whose catalogue `packages/agents/centinela_agents/catalog.py:catalog_from_kernel(answer)` builds from its answer; a person through `apps/api`, decided | lists the client's KPIs, base and approved, with their card, entity, columns and whether each is descriptive |

The generator does not call `kpi_validar`: it compiles each block and applies the `costo` guard
itself, against the database `CENTINELA_DSN` names, on its `fecha_corte()`.

A refusal returns as `{"rechazado": {"guarda", "detalle"}}`, so the model reads which guard
refused. A database error that is no guard, such as an approved KPI whose stored text writes,
surfaces as a tool error. The model names a KPI by id and never passes SQL.
`centinela_tools/kernel.py:Kernel.call(name, arguments)` checks the arguments against the tool's
schema in `centinela_tools/kernel.py:CONTRACT` before it runs, so arguments out of contract return
as a `lenguaje` refusal, and a name outside the contract is an error.
`centinela_tools/kernel.py:kernel_from_env(env)` builds the catalogue from the entries of
`data/metricas.yaml` with a `kernel:` block and from the approved-KPI file, so a base entry the
language refuses stops it, and so does an approved id that repeats or that a base KPI holds.

### The approved-KPI file

> **Decided, not built.** No code writes the file, and `apps/api` has no catalogue.

`CENTINELA_KPIS_APROBADOS` names a JSON list, one record per approved KPI with `id`, `ficha`,
`descriptivo`, `entidad`, `columnas`, `sql`, `hash` and `version_compilador`, which
`centinela_tools/tools.py:catalogue_of(entries, sources, approved)` reads; with no variable the
catalogue holds only the base KPIs. The orchestrator, which is code, writes that file as `apps/api`
hands it the client's approved KPIs.

## Base-KPI parity

**Parity is checked in two halves.** On `fecha_corte()`, the last day of the dataset, the kit's
views are right by definition, so each base KPI returns its view's rows, value for value, on the
columns the view holds. On earlier simulated days the views leak
([the clock](../../data/AGENTS.md#the-simulated-clock)), so each KPI agrees with a hand-written
as-of query on each day of `tests/test_parity.py:DAYS`, never with the view. `dias_pago_prom` has
only the second half, because its view measures by month of invoice.
`tests/test_parity.py:VIEWS` holds the view of each metric that has one and
`tests/test_parity.py:AS_OF` its as-of query, and the suite fails when a metric of
`data/metricas.yaml` is missing from either. Its header states the comparisons that depart and
why; each test is a `KER-` case of [`../../evals/AGENTS.md`](../../evals/AGENTS.md).

## Adding to this level

### A KPI

1. Write its entry in `data/metricas.yaml` with a `kernel:` block, its card and its `umbrales`,
   by the rules of [`../../data/AGENTS.md`](../../data/AGENTS.md#the-base-kpis).
2. Run `uv run python -m centinela_tools.generate` with `CENTINELA_DSN` naming the scratch database.
   A refusal names its guard.
3. Add its view query to `tests/test_parity.py:VIEWS`, when a view measures it, and its as-of query
   to `tests/test_parity.py:AS_OF`.
4. Run `uv run pytest` with `CENTINELA_TEST_DSN` set.
5. Commit `data/sql/05_kpis.generated.sql` with the entry; `tests/test_generate.py` fails while the
   two differ.
6. Follow the tree's steps for a metric in
   [`../agents/arbol/AGENTS.md`](../agents/arbol/AGENTS.md#adding-to-the-tree).

### A guard

1. Add its name to `centinela_tools/refusal.py:GUARDS`, and raise
   `centinela_tools/refusal.py:Refused` with it where the check runs; a setting goes in
   `centinela_tools/settings.py:Settings`.
2. Add its row to the guard table above.
3. Plant one violation it refuses in the test of the layer that checks it: `tests/test_language.py`,
   `tests/test_compiler.py`, `tests/test_tools.py`, or `tests/test_tools_db.py` when it needs the
   database.
4. Run `uv run pytest`.

### A tool

1. A kernel tool is an entry of `centinela_tools/kernel.py:CONTRACT`, a branch of
   `centinela_tools/kernel.py:Kernel.run(name, arguments)` and a function in
   `centinela_tools/tools.py`; `tests/test_kernel.py` holds the contract to its four tools, so the
   change is made there on purpose. No kernel tool takes SQL.
2. Any other tool is a module under `centinela_tools/`, served as [its MCP server](#the-other-tools).
3. It connects as `centinela_lector` through `CENTINELA_LECTOR_DSN`, or as `centinela_kernel`
   through `CENTINELA_KERNEL_DSN`, and never as a role that writes. An action produces a draft or a
   sandbox effect and is idempotent.
4. Write on this page what it can touch and why the agents need it, then which agent is given it in
   [`../agents/AGENTS.md`](../agents/AGENTS.md).
5. Plant one violation per bound it holds, and run `uv run pytest`.
