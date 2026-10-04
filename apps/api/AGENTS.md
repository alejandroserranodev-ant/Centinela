# apps/api: the API, the clock and the log

This level is the only door into Centinela: the web, the jury and any script reach the agents
through it. What runs here is a FastAPI app over its own PostgreSQL schema `api`. It serves the
brief's minimal endpoints, owns the simulated clock, the alert lifecycle and the `bitácora`, and
runs the orchestrator of `packages/agents` in its own process on each day advance and each
decision. Detection and the agents read the kernel's KPIs on the simulated day, so every alert and
every figure comes from the dataset. The sections marked below hold decisions the code does not
implement.

## Why each file exists

| File | Why it exists |
|---|---|
| `pyproject.toml` | the `centinela-api` package, built with setuptools from `src/`; it depends on `centinela-agents`, which `[tool.uv.sources]` points at `../../packages/agents`; its `dev` extra adds pytest and httpx, and its pytest config declares the `integracion` marker |
| `sql/01_esquema.sql` | creates the schema `api`: `api.simulacion`, `api.alertas`, `api.bitacora`, `api.consultas` |
| `src/centinela_api/main.py` | builds the app, opens CORS to any origin and mounts the routers |
| `src/centinela_api/config.py` | loads the root's `.env` and `.env.local` and holds `DSN_ADMIN`, `AGENT_SECRET_KEY`, `AUTH_SECRET_KEY` and the raw `CENTINELA_USUARIOS` |
| `src/centinela_api/auth.py` | the profiles, the password check, the token and `persona_actual(authorization)`, the dependency that names the person |
| `src/centinela_api/permisos.py` | who owns a metric, who may decide an alert, who may configure |
| `src/centinela_api/db.py` | `obtener_conexion()`, one connection per request as a FastAPI dependency, with no pool |
| `src/centinela_api/modelos.py` | the Pydantic models, the HTTP contract's source; their conventions are [`../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md`](../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md) |
| `src/centinela_api/contrato.py` | `esquema()`, the OpenAPI document plus the payloads of the event streams, and `exportar(destino)`, which `python -m centinela_api.contrato` runs to write `../web/src/api/openapi.json` |
| `src/centinela_api/ciclo_vida.py` | the lifecycle's transitions and the Spanish names it accepts at the edge |
| `src/centinela_api/decisiones.py` | `aplicar(alerta, decision)`, the pure check of a person's decision |
| `src/centinela_api/alertas.py` | reads and upserts `api.alertas` |
| `src/centinela_api/bitacora.py` | appends to and lists `api.bitacora` |
| `src/centinela_api/consultas.py` | records and reads `api.consultas`, the kernel call behind each `queryId` an agent cited |
| `src/centinela_api/simulacion.py` | reads and advances the clock |
| `src/centinela_api/sse.py` | `flujo(eventos)`, which turns `(event, model)` pairs into a server-sent event stream |
| `src/centinela_api/agentes.py` | the bridge to `packages/agents`: the orchestrator, the walk's context and the state-to-`Alert` conversion |
| `src/centinela_api/masking.py` | deterministic masks for client, vendor and product names and ids |
| `src/centinela_api/routers/` | one router per resource: `auth`, `simulacion`, `alertas`, `chat`, `bitacora`, `consultas`, `interno` |
| `tests/` | `tests/test_ciclo_vida.py`, `tests/test_decisiones.py` and `tests/test_manifest.py`, `tests/test_contrato.py` and `tests/test_auth.py` are pure; `tests/test_flujo_agentes.py`, `tests/test_avanzar.py`, `tests/test_ciclo_orquestado.py`, `tests/test_chat.py` and `tests/test_permisos.py` mock the database; `tests/test_api_integracion.py` needs Postgres |

## Commands

From this directory, with Python 3.12 or later, because `packages/agents` asks for it:

```bash
pip install -e ../../packages/tools -e ../../packages/agents -e ".[dev]"
psql "$DSN_ADMIN" -f sql/01_esquema.sql
uvicorn centinela_api.main:app --reload
pytest
pytest -m integracion
```

- **`centinela-agents`, and the `centinela-tools` it declares, are dependencies no index
  serves**, so pip installs them only from the paths the same command names, and a plain
  `pip install -e .` stops with no matching distribution. `uv pip install -e ".[dev]"` reads the path from `[tool.uv.sources]` and needs
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
`apps/web/src/api/http-client.ts`. Every route but `/auth/login`, the docs and `/interno/*` needs
a bearer token, and answers 401 without a valid one.

| Method | Path | Serves | Refuses | Web function |
|---|---|---|---|---|
| POST | `/auth/login` | a `Sesion`, token and `Persona`, for `Credenciales` | 401, one message for any failure | `login` |
| GET | `/auth/sesion` | the `Persona` of the token | 401 | `getSession` |
| GET | `/simulacion/dia-actual` | the simulated day, as `SimulatedDay` | | `getSimulatedDay` |
| POST | `/simulacion/avanzar?dias=1` | advances the clock and runs the day; streams `step` events, each an `AgentStep`, per detection and one `end` with `simulatedDay` and `newAlerts` | 422 when `dias` is below one | `advanceDay` |
| GET | `/alertas?estado=propuesta` | the alerts, filtered by the Spanish `estado`, ordered by pesos at risk | 422 for an unknown `estado` | `listAlerts` |
| GET | `/alertas/{id}` | one alert: cause, evidence and actions | 404 for an unknown alert | `getAlert` |
| POST | `/alertas/{id}/decision` | `approve`, `edit` or `reject` | 404; 403 for a person who may not decide it; 409 when the alert is not `proposed`; 422 for a failed check | `decide` |
| POST | `/chat` | a question of at most `MAX_QUESTION` characters and its optional `alertId`, answered by one SSE `step` per node the chat walked and one `end` with a `ChatMessage` and its `outcome` | 404 for an unknown alert; 422 for an empty or longer question | `chat` |
| GET | `/consultas/{queryId}` | the kernel call behind a figure, as `Query` | 404 for an unknown query | `getQuery` |
| GET | `/bitacora?alertId=&type=` | the log, newest first, filtered by alert and event type | | `listBitacora` |

**`/chat` runs the agent `Chat`.** `src/centinela_api/routers/chat.py:chat(pregunta, quien, conn)`
reads the simulated day and the anchored alert, logs the question under the person signed in, and
calls
`packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.ask(question, day, alert)`
through `asyncio.to_thread`. It streams one `step` per node with a Spanish description, then the
`end`, whose figures pass through `src/centinela_api/agentes.py:_convert_figures(raw)` and whose
`outcome` names the end the walk reached. A failed model call answers `no_evidence`, never an
error, and its step and kind join the `answer` row, so the log never reads an outage as a refusal.

**`/consultas/{queryId}` serves the call, never runs it**: `api.consultas` holds each
`kpi_consultar` a leaf ran, with its KPI and day, written by the day run and by the chat, so a figure
opens its source after the process that cited it is gone.

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
| GET | undecided | the inbox totals | | `getInboxSummary` |
| GET | undecided | the watched KPIs, thresholds, owners and autonomy per action type | | `getSettings` |
| undecided | undecided | saves the settings whole | 422 when any action type's autonomy is `execute` | `saveSettings` |

**The KPI catalogue's endpoints**, which list the base and approved KPIs and let the administrator
decide a proposed KPI or retire one, are decided by the pending work on a new KPI's lifecycle, and
become rows here when it is planned.

### Adding an endpoint

1. Add its row to the table above first: method, path, what it serves, what it refuses, and the
   web function that consumes it.
2. Write its models in `src/centinela_api/modelos.py`, following
   [`../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md`](../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md);
   then run `python -m centinela_api.contrato` to export the contract the web generates its types
   from; `tests/test_contrato.py` fails until it does.
3. Write it in the router of its resource, with `response_model` set, and mount a new router in
   `src/centinela_api/main.py`.
4. A test beside the others: pure when the logic allows it, `integracion` when it needs Postgres.

## The agents run in this process

**`src/centinela_api/agentes.py` builds the orchestrator once, lazily**, in
`get_orchestrator()`: `CentinelaOrchestrator` from `packages/agents`, with the provider of
`get_provider()` and `get_reasoning_provider()`, the tree `packages/agents/arbol/base.yaml`, the
thresholds of `data/metricas.yaml`, the kernel `get_kernel()` connects through
`packages/agents/centinela_agents/catalog.py:connect_kernel(env)`, a `ToolRegistry` of the four action stubs and an
`InMemorySaver`. The routers call
`start`, `resume` and `ask` through `asyncio.to_thread`, because the graph runs synchronously and the
event loop keeps streaming SSE meanwhile. Running in-process saves a service boundary, its
transport and its secret, and is the answer to whether the agents run here or as a service.

- **The checkpointer is `InMemorySaver`**, the saver that needs no schema. A paused alert lives
  only in this process: after a restart its decision is recorded but the resume finds no state, a
  `result` row of `ejecutor` records that the approved action did not run, and the alert stays
  `approved`.
- **A day raises the alerts `src/centinela_api/agentes.py:prioritized(detections, known)` keeps**:
  the detections of `API_METRICS` whose alert does not exist, the most `pesos_en_riesgo` first, at
  most `CENTINELA_ALERTAS_POR_DIA`, read on each call so a test can lower it. An alert's id is
  `src/centinela_api/agentes.py:alert_id_of(detection)`, a hash of metric and entity, so one alert
  per metric and entity holds by the primary key. Why the cap and the order is
  [`../../packages/agents/AGENTS.md`](../../packages/agents/AGENTS.md#the-day-run).
- **`state_to_alert(alert_id, state, detection, day_str)` reads the graph's state**: the title,
  the cause and the actions with the figures the leaves cited, pesos at risk from the KPI's
  `pesos_en_riesgo` under the `queryId` the leaves recorded, and the cause's confidence. A figure
  with no `queryId` is dropped, never given one. Severity alone is a heuristic over the detected
  row, because nothing in the tree defines it.
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

**A person signs in; every route reads the person from the token.** The profiles are
`CENTINELA_USUARIOS` in the root `.env`, each `clave` a PBKDF2 hash from
`python -m centinela_api.auth hash`, because that file is public; a malformed list stops the API.
`src/centinela_api/auth.py:verificar(correo, clave)` hashes even for an unknown email, so nothing
tells which half failed. The token signs the email and an eight-hour expiry with
`AUTH_SECRET_KEY`, and the person is re-read from the profiles. Full enterprise authentication
stays out of scope.

**Who decides is checked first.** `src/centinela_api/permisos.py:puede_decidir(persona, alerta)`
lets the `gerente` decide any alert and a `lider_proceso` those whose metric its `area` owns in
`packages/agents/skills/estratega/acciones.md`. Anyone else gets 403, which names the owner: the
request is valid, the person may not make it. Each alert returned carries `decidedBy` and
`canDecide`, never stored, so the screen decides no permission. Then
`src/centinela_api/decisiones.py:aplicar(alerta, decision)` requires `proposed` (409), a
rejection's reason and one of the alert's actions (422). The decision and its `bitácora` row
commit before the orchestrator resumes, so no action runs unrecorded.

> **Decided, not built.** The rules below, where the code differs as each one says.

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
time, and the alert it belongs to, which a chat question asked from no alert leaves empty.

| Type | Written by |
|---|---|
| `alert` | `avanzar`, for each alert the orchestrator returns; `POST /interno/alertas` |
| `evidence` | `avanzar`, one row per `kpi_consultar` a leaf ran, its SQL as the detail and its `queryId`; `PUT /interno/alertas/{id}/causa` |
| `proposal` | `PUT /interno/alertas/{id}/propuesta` |
| `decision` | a person's decision |
| `action` | `POST /interno/alertas/{id}/ejecutar` |
| `result` | the resume after an approval, when `Ejecutor` returns an executed action |
| `question` | `/chat`, the person's question with its email addresses and keys masked |
| `evidence`, from the chat | `/chat`, one row per query the chat ran and one per model step's cost |
| `answer` | `/chat`, the end and the text of an answer, with its first figure's `queryId` |
| `refusal` | `/chat`, a question the screen flagged, one outside the chat's use, or one asking to act |

On the path that runs, a day's alert lands with its `alert` row, which cites the KPI's `queryId`,
and one `evidence` row per query its leaves ran, so every figure of the alert resolves to the SQL
that returned it; an approval adds its `decision` and `result`. The graph's proposal leaves no row
of its own.

## Rules of this level

- **No decision, no action.** The API resumes an alert past the approval interrupt only after the
  decision is committed with its role. *No gate holds this.*
- **The API's state lives in its own schema `api`**, created by `sql/01_esquema.sql` with
  `IF NOT EXISTS`, never in the dataset's `centinela` schema. The file runs again on a database it
  built before: its `ALTER`s on `api.bitacora` give the table the shape a new one has, so there is
  no migration tool. *No gate holds this.*

> **Decided, not built.** The three rules below, where the code differs as each one says.

- **An alert carries its cost**: the API persists the tokens and model calls the orchestrator
  counts per alert, as `/chat` already logs each step of a chat answer. `api.alertas.costos` exists and nothing writes it;
  `_registrar_costo` records a step's cost sent by `X-Cost-Json` as an `evidence` row and swallows
  any error.
- **Timeouts and retries are explicit**, as the orchestrator's graph states them, and "not enough
  evidence" is a valid response, not an error. The code logs a failed detection or resume and
  skips it.
- **The project is a uv project**, with its lockfile beside this page, as `packages/agents` and
  `packages/tools` are. It is a setuptools package installed with pip.
