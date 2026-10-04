# apps/api: the API, the clock and the log

This level is the only door into Centinela: the web, the jury and any script reach the agents
through it. What runs here is a FastAPI app over its own PostgreSQL schema `api`. It serves the
brief's minimal endpoints, owns the simulated clock, the alert lifecycle and the `bitácora`, and
runs the orchestrator of `packages/agents` in its own process on each day advance and each
decision. The KPIs the orchestrator reads on that path are demo rows, not the kernel, so no alert
comes from the dataset. The sections marked below hold decisions the code does not implement.

## Why each file exists

| File | Why it exists |
|---|---|
| `pyproject.toml` | the `centinela-api` package, built with setuptools from `src/`; it depends on `centinela-agents`, which `[tool.uv.sources]` points at `../../packages/agents`; its `dev` extra adds pytest and httpx, and its pytest config declares the `integracion` marker |
| `sql/01_esquema.sql` | creates the schema `api`: `api.simulacion`, `api.alertas`, `api.bitacora` |
| `src/centinela_api/main.py` | builds the app, opens CORS to any origin and mounts the routers |
| `src/centinela_api/config.py` | loads the root's `.env` and `.env.local` and holds `DSN_ADMIN`, `AGENT_SECRET_KEY` and `ROLES_CON_DECISION` |
| `src/centinela_api/db.py` | `obtener_conexion()`, one connection per request as a FastAPI dependency, with no pool |
| `src/centinela_api/modelos.py` | the Pydantic models, the HTTP contract's source; their conventions are [`../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md`](../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md) |
| `src/centinela_api/ciclo_vida.py` | the lifecycle's transitions and the Spanish names it accepts at the edge |
| `src/centinela_api/decisiones.py` | `aplicar(alerta, decision)`, the pure check of a person's decision |
| `src/centinela_api/alertas.py` | reads and upserts `api.alertas` |
| `src/centinela_api/bitacora.py` | appends to and lists `api.bitacora` |
| `src/centinela_api/simulacion.py` | reads and advances the clock |
| `src/centinela_api/sse.py` | `flujo(eventos)`, which turns `(event, model)` pairs into a server-sent event stream |
| `src/centinela_api/agentes.py` | the bridge to `packages/agents`: the orchestrator, the walk's context and the state-to-`Alert` conversion |
| `src/centinela_api/masking.py` | deterministic masks for client, vendor and product names and ids |
| `src/centinela_api/routers/` | one router per resource: `simulacion`, `alertas`, `chat`, `bitacora`, `interno` |
| `tests/` | `tests/test_ciclo_vida.py`, `tests/test_decisiones.py`, `tests/test_chat.py` and `tests/test_manifest.py` are pure; `tests/test_flujo_agentes.py`, `tests/test_avanzar.py` and `tests/test_ciclo_orquestado.py` mock the database; `tests/test_api_integracion.py` needs Postgres |

## Commands

From this directory, with Python 3.12 or later, because `packages/agents` asks for it:

```bash
pip install -e ../../packages/agents -e ".[dev]"
psql "$DSN_ADMIN" -f sql/01_esquema.sql
uvicorn centinela_api.main:app --reload
pytest
pytest -m integracion
```

- **`centinela-agents` is a declared dependency that no index serves**, so pip installs it only
  from the path the same command names, and a plain `pip install -e .` stops with no matching
  distribution. `uv pip install -e ".[dev]"` reads the path from `[tool.uv.sources]` and needs
  none. `tests/test_manifest.py` fails when a module imports a distribution the manifest does not
  declare.
- **`sql/01_esquema.sql` runs after the dataset's SQL files**, because the clock seeds
  itself from `centinela.fecha_corte()`. The database setup is
  [`../../data/AGENTS.md`](../../data/AGENTS.md#setting-up-the-database).
- **`pytest` runs every test.** `tests/test_api_integracion.py` skips itself when `DSN_ADMIN` reaches no database;
  every test that imports `centinela_api.main` needs `centinela_agents` and LangGraph installed.
- **`src/centinela_api/config.py` loads the root's `.env`, then `.env.local` over it**, both by
  path, so the API reads the same values wherever it starts. The `.env` is versioned without
  secrets, because the competition's rules ask for it; a key goes in the ignored `.env.local`. The
  orchestrator reads `LLM_PROVIDER` and `LLM_MODEL` from it
  ([`../../SETUP_OPENAI.md`](../../SETUP_OPENAI.md)).

## Endpoints

The brief's minimal API is [`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its
minimal API section; its paths stay as the brief writes them. The web consumes them through
`apps/web/src/api/http-client.ts`.

| Method | Path | Serves | Refuses | Web function |
|---|---|---|---|---|
| GET | `/simulacion/dia-actual` | the simulated day, as `SimulatedDay` | | `getSimulationState` |
| POST | `/simulacion/avanzar?dias=1` | advances the clock and runs the day; streams `step` events, each an `AgentStep`, per detection and one `end` with `simulatedDay` and `newAlerts` | 422 when `dias` is below one | `advanceDay` |
| GET | `/alertas?estado=propuesta` | the alerts, filtered by the Spanish `estado`, ordered by pesos at risk | 422 for an unknown `estado` | `listAlerts` |
| GET | `/alertas/{id}` | one alert: cause, evidence and actions | 404 for an unknown alert | `getAlert` |
| POST | `/alertas/{id}/decision` | `approve`, `edit` or `reject`, with headers `X-User-Name` and `X-User-Role` | 403 for a role that may not decide; 404; 409 when the alert is not `proposed`; 422 for a failed check | `decide` |
| POST | `/chat` | a question, answered by SSE `step` and `end` events | | `chat` |
| GET | `/bitacora?alertId=&type=` | the log, newest first, filtered by alert and event type | | `listBitacora` |

**`/chat` calls no agent.** `src/centinela_api/routers/chat.py:chat(pregunta)` takes the question
and the optional `alertId` it is asked from, and answers a fixed "sin evidencia suficiente". It
costs the brief's chat, and is paid when the question reaches `Analista`.

**The internal endpoints `/interno/*` have no caller.** `src/centinela_api/routers/interno.py`
lets an agent write each stage over HTTP: `POST /interno/alertas` (`Vigía`), `PUT .../causa`
(`Analista`), `PUT .../propuesta` (`Estratega`), `POST .../ejecutar` (`Ejecutor`). Each checks
`X-Agent-Key` against `AGENT_SECRET_KEY` (401), `X-Agent` against the stage (400) and the
transition (409). The agents run in this process, so they cost a second write path to keep
consistent with the first, paid when they are wired or removed.

> **Decided, not built.** These rows; each path is chosen with the code, in Spanish like the
> brief's.

| Method | Path | Serves | Refuses | Web function |
|---|---|---|---|---|
| GET | undecided | the person signed in, with a role | | `getSimulationState` |
| GET | undecided | the inbox totals | | `getInboxSummary` |
| GET | undecided | the watched KPIs, thresholds, owners and autonomy per action type | | `getSettings` |
| undecided | undecided | saves the settings whole | 422 when any action type's autonomy is `execute` | `saveSettings` |
| GET | undecided | one query by id, for "how I got here" | 404 for an unknown query | `getQuery` |

**The KPI catalogue's endpoints**, which list the base and approved KPIs and let the administrator
decide a proposed KPI or retire one, are decided by the pending work on a new KPI's lifecycle, and
become rows here when it is planned.

### Adding an endpoint

1. Add its row to the table above first: method, path, what it serves, what it refuses, and the
   web function that consumes it.
2. Write its models in `src/centinela_api/modelos.py`, following
   [`../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md`](../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md);
   `apps/web/src/api/types.ts` follows them field for field.
3. Write it in the router of its resource, with `response_model` set, and mount a new router in
   `src/centinela_api/main.py`.
4. A test beside the others: pure when the logic allows it, `integracion` when it needs Postgres.

## The agents run in this process

**`src/centinela_api/agentes.py` builds the orchestrator once, lazily**, in
`get_orchestrator()`: `CentinelaOrchestrator` from `packages/agents`, with the provider of
`get_provider()`, the tree `packages/agents/arbol/base.yaml`, the thresholds of
`data/metricas.yaml`, an empty `ToolRegistry` and an `InMemorySaver`. The routers call
`start` and `resume` through `asyncio.to_thread`, because the graph runs synchronously and the
event loop keeps streaming SSE meanwhile. Running in-process saves a service boundary, its
transport and its secret, and is the answer to whether the agents run here or as a service.

- **The checkpointer is `InMemorySaver`**, the saver that needs no schema. A paused alert lives
  only in this process: after a restart its decision is recorded but the resume finds no state,
  logs a warning, and the alert stays `approved` with no action run.
- **Detection reads demo rows.** `get_context()` and the orchestrator get `_demo_reader(metric, day)`,
  which returns the same rows of `saldo_vencido` and `cobertura_dias` whatever the day, so every
  advance raises those alerts again under new ids. It costs every alert its link to the data, and
  is paid when the reader is the kernel's `kpi_consultar`
  ([`../../packages/tools/AGENTS.md`](../../packages/tools/AGENTS.md)).
- **`VIEW_CATALOG` copies the catalogue of `packages/agents/tests/support.py`**, so the two drift
  apart unless both are edited.
- **`state_to_alert(alert_id, state, detection, day_str)` fills what the graph does not return**:
  severity and pesos at risk from heuristics over the detected row, confidence `medium`, and no
  recoverable per month. These figures cite the query id `q_detect`, which no query catalogue
  holds.
- **Only the metrics `API_METRICS` names become alerts**, because the `Alert` model's `Metric`
  accepts no other.

## The clock

**The API owns the simulated clock**, the single row of `api.simulacion`. The first read seeds
it from `centinela.fecha_corte()`; `src/centinela_api/simulacion.py:avanzar(conn, dias)` adds
days. The day it moves replaces `fecha_corte()` (see
[`../../data/AGENTS.md`](../../data/AGENTS.md#the-simulated-clock)), and it reaches the
orchestrator as the argument of each run.

> **Decided, not built.** The two decisions below.

**One day run at a time.** A call to `/simulacion/avanzar` while a day run is in course is refused
with 409, because the second run would detect against earlier alerts the first has not
recorded, and one cause would raise two alerts.

**The API hands each run what the orchestrator cannot read**: the metric, entity, severity and
state of every earlier alert, and the rejection reasons kept for the alert's metric. It keeps each
reason with the target the orchestrator classified it to, the metric and the entity. `avanzar`
calls `start` without them.

## The alert lifecycle

**The contract and the database speak English statuses**: `new`, `analyzing`, `proposed`,
`approved`, `rejected`, `executed`. The Spanish names stay at the edge: `estado=propuesta` on
`GET /alertas` is the brief's spelling, and
`src/centinela_api/ciclo_vida.py:ESTADO_A_STATUS` maps it.

**`src/centinela_api/ciclo_vida.py:transicionar(actual, siguiente)` refuses a transition
`TRANSICIONES` does not list**: `new` → `analyzing` → `proposed` → `approved` or `rejected`, and
`approved` → `executed`. A person's decision and the internal routes call it, and so do the two
paths the orchestrator drives. `avanzar` hands
`src/centinela_api/ciclo_vida.py:recorrer(estados)` the statuses the graph took the alert through,
read from its `transitions` by `src/centinela_api/agentes.py:status_path(alert_id, state)`, and
stores no alert whose path does not start at `new` or skips a transition. The resume after an
approval writes `executed` only after `transicionar` accepts it from `approved`. The database
keeps the last status, not the path.

> **Decided, not built.** The table below and the merge it carries. The graph's `unida` reaches
> the API as `new`, because `state_to_alert` has no entry for it.

**The API validates every transition and persists it.** The orchestrator proposes the transitions
an agent causes, because it is the only part that sees an agent finish; the API proposes the ones
a person causes. The record is the API's, because it is the only part with storage and the only
door. How the orchestrator reaches each proposal is
[`../../packages/agents/AGENTS.md`](../../packages/agents/AGENTS.md), its graph section.

| Transition | Proposed by |
|---|---|
| → `nueva` | the orchestrator, when `Vigía` detects |
| `nueva` → `en análisis` | the orchestrator, when the title is written |
| `en análisis` → `propuesta` | the orchestrator, when `Estratega` proposes |
| `en análisis` → `unida` | the orchestrator, when it merges the alert into one analysed before it |
| `nueva` → `unida` | the orchestrator, when an alert of the same day, analysed first because its pesos at risk are larger, names this one as the same cause |
| `propuesta` → `aprobada` or `rechazada` | the API, from a person's decision |
| `aprobada` → `ejecutada` | the orchestrator, when `Ejecutor` returns its result |

- **`unida` is a state the brief's lifecycle does not have.** An alert whose cause `Analista` finds
  already explains another alert ends there, pointing to the alert that remains, because the brief
  asks that one cause raise one alert and its lifecycle has no end for the second. `rechazada`
  would claim a decision no person made, so `unida` is final and never counts as decided.
- **A merge keeps one alert in view and loses nothing.** The API accepts a transition to `unida`
  only while its target is in `nueva`, `en análisis` or `propuesta`, checked in the transaction
  that records it, so every alert of one cause points to the one that remains and none points to a
  merged alert. The inbox lists only the alert that remains, and its detail carries, beside its
  own, the detection and evidence of each alert in its `merged_alerts`. Its pesos at risk stay its
  own, because two detections of one cause would count the same pesos twice.

## Decisions and roles

**The API checks a decision before it resumes an alert.**
`src/centinela_api/decisiones.py:aplicar(alerta, decision)` requires the alert in `proposed`
(409), a rejection to carry a reason (422), and an approval or an edit to name one of the alert's
actions (422). The router first checks `X-User-Role` against `ROLES_CON_DECISION`, `gerente` and
`lider_proceso`, and answers 403. `X-User-Name` arrives percent-encoded, because a header is ASCII
and Colombian names are not. The decision and its `bitácora` row commit in one transaction before
the orchestrator resumes, so no action runs without a recorded decision; an approval or an edit
then resumes into `Ejecutor`, and a rejection resumes to close the graph.

**Full enterprise authentication is out of scope; roles are not.** There is no login: the role is
whatever the header says.

> **Decided, not built.** The rules below, where the code differs as each one says.

- **The role that decides an alert is the owner of its metric** in the settings, among the roles
  the policies name, such as `Gerente comercial` or `Jefe de cartera`; the `administrador` role
  decides the KPI catalogue. The code holds a fixed pair of roles for every alert.
- **A failed role check answers 422**, like every other check of a decision. The code answers 403.
- **An edit keeps the keys of the action's `parameters`, adding none and dropping none**, because
  `Ejecutor` passes them unchanged. `aplicar` merges the edit into them, so a new key passes.
- **A `request_changes` carries a reason, and is capped at one per alert**, because a person who
  still disagrees after one new proposal has the decision in hand: an edit says what to change
  and a rejection says why, and both close the alert. The alert stays `propuesta` while
  `Estratega` proposes again, and the reason joins the rejection reasons `Estratega` reads. The
  `Decision` union has no such kind.
- **"Ejecuta" is refused for every action type**, with 422 on saving the settings, because the
  challenge keeps every action at `Propone` ([`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md),
  its responsible AI section).

**Personal data reaches the models unmasked.** `src/centinela_api/masking.py:mask_dict_for_model(data)`
replaces client and vendor ids and names with a hash-suffixed placeholder, the same for the same
input, but no route calls it, and `mask_text_evidence` replaces only the pairs it is handed. It
costs the challenge's Ley 1581 requirement on every model call, and is paid when the data a model
reads goes through it, in this level or in `packages/tools`, whose page owns masking.

## The inbox totals

> **Decided, not built.**

**The API computes the inbox totals**: pesos at risk today and recoverable per month, each a sum
over the alerts in `propuesta`, and the count of decisions pending. They are sums over alerts
rather than a `v_*` view, so the API sends each as a figure whose query reads its own alerts
table, and the screen computes none.

## The `bitácora`

**`api.bitacora` is append-only**: `src/centinela_api/bitacora.py:registrar(conn, alerta_id, tipo, actor, detalle, dia_simulado, query_id)`
inserts, and no code updates or deletes a row; no grant enforces it. Each row carries its type,
its actor, an agent or a person with name and role, its detail, the simulated day and the real
time.

| Type | Written by |
|---|---|
| `alert` | `avanzar`, for each alert the orchestrator returns; `POST /interno/alertas` |
| `evidence` | `PUT /interno/alertas/{id}/causa`, and the cost of a step |
| `proposal` | `PUT /interno/alertas/{id}/propuesta` |
| `decision` | a person's decision |
| `action` | `POST /interno/alertas/{id}/ejecutar` |
| `result` | the resume after an approval, when `Ejecutor` returns an executed action |

On the path that runs, a day's alert lands with only its `alert` row, and an approval with its
`decision` and `result`: the graph's analysis and proposal leave no row.

## Rules of this level

- **No decision, no action.** The API resumes an alert past the approval interrupt only after the
  decision is committed with its role. *No gate holds this.*
- **The API's state lives in its own schema `api`**, created by `sql/01_esquema.sql` with
  `IF NOT EXISTS` and no migrations, never in the dataset's `centinela` schema. *No gate holds
  this.*

> **Decided, not built.** The three rules below, where the code differs as each one says.

- **An alert carries its cost**: the API persists the tokens and model calls the orchestrator
  counts per alert, and per chat answer. `api.alertas.costos` exists and nothing writes it;
  `_registrar_costo` records a step's cost sent by `X-Cost-Json` as an `evidence` row and swallows
  any error.
- **Timeouts and retries are explicit**, as the orchestrator's graph states them, and "not enough
  evidence" is a valid response, not an error. The code logs a failed detection or resume and
  skips it.
- **The project is a uv project**, with its lockfile beside this page, as `packages/agents` and
  `packages/tools` are. It is a setuptools package installed with pip.
