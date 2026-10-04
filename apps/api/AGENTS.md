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
| `sql/01_esquema.sql` | creates the schema `api`: `api.simulacion`, `api.alertas`, `api.bitacora`, `api.consultas` with its `fuente`, `api.configuracion`, `api.arbol_versiones`, `api.rechazos`; `api.alertas` holds `entidad`, the values of the KPI's entity, which coverage compares, `costos`, the alert's `cost` by agent, and `arbol_version`, the version of the tree it walked ([`../../DOUBTS.md`](../../DOUBTS.md#filed-debts) files its default) |
| `src/centinela_api/main.py` | builds the app, opens CORS to any origin, mounts the routers and logs every package at INFO |
| `src/centinela_api/config.py` | loads the root's `.env` and `.env.local` and holds `DSN_ADMIN`, `AGENT_SECRET_KEY`, `AUTH_SECRET_KEY` and the raw `CENTINELA_USUARIOS` |
| `src/centinela_api/auth.py` | the profiles of `CENTINELA_USUARIOS`, the password check, the signed token and `persona_actual(authorization)`, the dependency every route but the sign-in and `/interno/*` reads its person from; `python -m centinela_api.auth hash` hashes a password read from stdin |
| `src/centinela_api/permisos.py` | who owns a metric, who may decide an alert and who may configure, and `vista(conn, persona, alerta)`, the alert as the person signed in reads it |
| `src/centinela_api/configuracion.py` | the settings: their seed, how a stored row merges with it, the checks of a save, and what the day run reads from them |
| `src/centinela_api/db.py` | `obtener_conexion()`, one connection per request as a FastAPI dependency, with no pool |
| `src/centinela_api/modelos.py` | the Pydantic models, the HTTP contract's source; their conventions are [`../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md`](../../REPORTE_JSON_SCHEMA_STANDARDIZATION.md) |
| `src/centinela_api/contrato.py` | `esquema()`, the OpenAPI document plus the payloads of the event streams, and `exportar(destino)`, which `python -m centinela_api.contrato` runs to write `../web/src/api/openapi.json` |
| `src/centinela_api/ciclo_vida.py` | the lifecycle's transitions and the Spanish names it accepts at the edge |
| `src/centinela_api/decisiones.py` | `aplicar(alerta, decision, autonomia)`, the pure check of a person's decision |
| `src/centinela_api/alertas.py` | reads and upserts `api.alertas` |
| `src/centinela_api/bitacora.py` | appends to and lists `api.bitacora` |
| `src/centinela_api/consultas.py` | records and reads `api.consultas`, the call behind each `queryId`: a kernel call an agent cited, or a total of the inbox |
| `src/centinela_api/resumen.py` | computes the inbox totals over `api.alertas` and records the query of each |
| `src/centinela_api/simulacion.py` | reads and advances the clock |
| `src/centinela_api/sse.py` | `flujo(eventos)`, which turns `(event, model)` pairs into a server-sent event stream |
| `src/centinela_api/agentes.py` | the bridge to `packages/agents`: the orchestrator, the walk's context and the state-to-`Alert` conversion |
| `src/centinela_api/arboles.py` | the tree's versions: the store, the replay over a new base, the growth of a day and the retirement of an expansion |
| `src/centinela_api/rechazos.py` | records each rejection the classifier targeted, with its metric and the actions it rejected, and lists them as evidence |
| `src/centinela_api/masking.py` | deterministic masks for client, vendor and product names and ids |
| `src/centinela_api/routers/` | one router per resource: `auth`, `simulacion`, `alertas`, `chat`, `bitacora`, `consultas`, `bandeja`, `configuracion`, `arbol`, `interno` |
| `tests/` | `tests/test_ciclo_vida.py`, `tests/test_decisiones.py` and `tests/test_manifest.py`, `tests/test_contrato.py` and `tests/test_auth.py` are pure; `tests/test_flujo_agentes.py`, `tests/test_avanzar.py`, `tests/test_ciclo_orquestado.py`, `tests/test_chat.py`, `tests/test_permisos.py`, `tests/test_configuracion.py`, `tests/test_arboles.py` and `tests/test_arbol.py` mock the database; `tests/test_api_integracion.py` needs Postgres |

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
`apps/web/src/api/http-client.ts`. Every route but `/auth/login`, the OpenAPI document and
`/interno/*` asks for `Authorization: Bearer <token>`, and answers 401 "Inicia sesión para
continuar", with `WWW-Authenticate: Bearer`, when the token is missing, altered or expired.

| Method | Path | Serves | Refuses | Web function |
|---|---|---|---|---|
| POST | `/auth/login` | `Credenciales` in, a `Sesion` out: the token and the `Persona` it belongs to | 401 "Correo o contraseña incorrectos", the same for an unknown email and a wrong password | `login` |
| GET | `/auth/sesion` | the `Persona` of the token | 401 | `getSession` |
| GET | `/simulacion/dia-actual` | the simulated day and `ultimoDia`, the last day with data, as `SimulatedDay` | | `getSimulatedDay` |
| POST | `/simulacion/avanzar?dias=1` | advances the clock and runs the day; streams one `step`, an `AgentStep`, as each agent of an alert starts and as it ends, opening with the detection, an `alert` event with each `Alert` stored or updated once it is recorded, with the person's `decidedBy` and `canDecide`, and one `end` with `simulatedDay` and `newAlerts`, the alerts that remain to decide | 422 when `dias` is below one; 409 `Ya hay un día en curso` while another run holds the lock, and 409 past the last day with data | `advanceDay` |
| GET | `/alertas?estado=propuesta` | the alerts, filtered by the Spanish `estado`, ordered by pesos at risk; without `estado`, every alert but the merged ones, which `estado=unida` lists | 422 for an unknown `estado` | `listAlerts` |
| GET | `/alertas/{id}` | one alert: cause, evidence and actions | 404 for an unknown alert | `getAlert` |
| POST | `/alertas/{id}/decision` | `approve`, `edit`, `reject` or `request_changes` | 404; 403 for a person who may not decide it; 409 when the alert is not `proposed`, when its graph no longer waits for a decision, or while another decision resumes it; 422 for a failed check | `decide` |
| POST | `/chat` | a question of at most `MAX_QUESTION` characters and its optional `alertId`, answered by one SSE `step` per node the chat walked and one `end` with a `ChatMessage` and its `outcome` | 404 for an unknown alert; 422 for an empty or longer question | `chat` |
| GET | `/bandeja/resumen` | the inbox totals, as `InboxSummary` | | `getInboxSummary` |
| GET | `/consultas/{queryId}` | the call behind a figure, as `Query`, `kernel` or `alertas`, with its first rows | 404 for an unknown query | `getQuery` |
| GET | `/bitacora?alertId=&type=` | the log, newest first, filtered by alert and event type | | `listBitacora` |
| GET | `/configuracion` | the `Settings`: watched metrics, their thresholds and owners, autonomy per action type | | `getSettings` |
| PUT | `/configuracion` | saves the `Settings` whole and returns them as stored | 403 unless analista or gerente; 422 for a failed check | `saveSettings` |
| GET | `/arbol/expansiones` | the expansions of the tree, newest first, as `TreeExpansion`: the agent, the change in Spanish, the alerts behind it, and its status, `active`, `retired` or `inactive`, with who retired it and why | | `listExpansions` |
| POST | `/arbol/expansiones/{id}/retiro` | retires an expansion with a `RetireExpansion` reason and returns it | 403 unless analista or gerente; 404 for an unknown expansion; 409 for one already retired; 422 for a blank reason, an `inactive` expansion, or one the validator refuses | `retireExpansion` |

**`/chat` runs the agent `Chat`.** `src/centinela_api/routers/chat.py:chat(pregunta, quien, conn)`
reads the simulated day and the anchored alert, logs the question under the person signed in, and
calls
`packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.ask(question, day, alert)`
through `asyncio.to_thread`. It streams one `step` per node with a Spanish description, then the
`end`, whose figures pass through `src/centinela_api/agentes.py:_convert_figures(raw)` and whose
`outcome` names the end the walk reached. A failed model call answers `no_evidence`, never an
error, and its `answer` row says the assistant could not finish, so the log never reads an outage
as a refusal.

**`/consultas/{queryId}` serves the call, never runs it**: `api.consultas` holds each
`kpi_consultar` a leaf ran, with its KPI and day, written by the day run and by the chat, so a figure
opens its source after the process that cited it is gone. An alert's own KPI is the call its
detection carries.

**The internal endpoints `/interno/*` have no caller.** `src/centinela_api/routers/interno.py`
lets an agent write each stage over HTTP: `POST /interno/alertas` (`Vigía`), `PUT .../causa`
(`Analista`), `PUT .../propuesta` (`Estratega`), `POST .../ejecutar` (`Ejecutor`). Each checks
`X-Agent-Key` against `AGENT_SECRET_KEY` (401), `X-Agent` against the stage (400) and the
transition (409). The agents run in this process, so they cost a second write path to keep
consistent with the first, paid when they are wired or removed.

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
thresholds of `data/metricas.yaml`, which the saved settings replace, the kernel `get_kernel()` connects through
`packages/agents/centinela_agents/catalog.py:connect_kernel(env)`, a `ToolRegistry` of the four action stubs and an
`InMemorySaver`. The routers call
`run_day`, `resume` and `ask` through `asyncio.to_thread`, because the graph runs synchronously and the
event loop keeps streaming SSE meanwhile. Running in-process saves a service boundary, its
transport and its secret, and is the answer to whether the agents run here or as a service.

- **No transaction stays open across a model call.** `src/centinela_api/db.py:conectar()` opens
  every connection with `autocommit`, so each `with conn.transaction()` is a real transaction that
  commits when its block ends, and no block holds an `await` or a `yield`. The routers run their
  SQL synchronously on the event loop, so a row lock is taken and released in one uninterrupted
  stretch of it, and a `FOR UPDATE` on the loop never waits for a holder that needs the loop to
  finish; running the SQL off the loop instead would cost a connection per thread for no gain.
- **The API runs one worker.** The day lock, the set of alerts a decision is resuming, the paused
  graphs and the random signing key live in the process, so a second worker would not see them.

- **The checkpointer is `InMemorySaver`**, the saver that needs no schema. A paused alert lives
  only in this process: after a restart its graph waits for nothing, so the decision route refuses
  its approval, edit or request for changes and records only its rejection, as decisions and roles
  states.
- **`avanzar` drives the day run of `packages/agents`**: it hands `run_day` every stored alert as
  an `Earlier`, through `src/centinela_api/agentes.py:earlier_of(alerta, entidad)`, the metrics
  `src/centinela_api/agentes.py:metricas_del_dia(ajustes)` names, the watched ones of
  `API_METRICS`, because the `Alert` model's `Metric` accepts no other, and the cap
  `CENTINELA_ALERTAS_POR_DIA`, read on each call so a test can lower it. It records each
  `AlertRun` with `src/centinela_api/routers/simulacion.py:_registrar(conn, corrida, dia, day_str, nota)`
  and sends back the verdict: not recorded when the lifecycle refuses a transition, the refused
  merge target, and the absorbed alerts it stored. It reads each result through
  `src/centinela_api/routers/simulacion.py:_siguiente(dia_en_curso, veredicto)`, because a
  `StopIteration` cannot cross `asyncio.to_thread`. Why the order, the cap and the id is
  [`../../packages/agents/AGENTS.md`](../../packages/agents/AGENTS.md#the-day-run). Before the run
  it takes the newest version of the tree from `src/centinela_api/arboles.py:del_dia(conn, dia)`
  and hands it to `packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.use_tree(tree)`,
  and `_registrar` stores each alert's `arbol_version`.
- **`src/centinela_api/agentes.py:state_to_alert(alert_id, state, detection, day_str)` reads the
  graph's state**: the title, the cause and the actions with the figures the leaves cited, and the
  cause's confidence. A figure with no `queryId` is dropped, never given one. Severity and pesos at
  risk come from the detection.

## The settings

**The settings live in the single row of `api.configuracion`**, which
`src/centinela_api/configuracion.py:leer(conn)` merges with
`src/centinela_api/configuracion.py:semilla()` and never writes. The seed is the metrics of
`API_METRICS` in `data/metricas.yaml`, all watched, each threshold of its `umbrales`, the owner
"The owner of a manual review" in `packages/agents/skills/estratega/acciones.md` names, and
`propose` for every action type. `owners` are the areas of the `lider_proceso` profiles, so an
owner none of them leads, such as `vendedor_id`, seeds as none and leaves the metric to the
`gerente`. A metric the row lacks reads its seed, a stored threshold whose key left the file is
dropped, and only a threshold that is one number is editable; the others always read the file.
A rule and a source reach the screen through
`src/centinela_api/configuracion.py:legible(texto)`, which names a column in business words,
because the file's text is also the agents' data.

**`src/centinela_api/configuracion.py:guardar(conn, nuevo, persona)` refuses with 422** an
`execute` autonomy, a changed non-editable threshold, a negative or non-finite value, an owner
outside `owners` and a list of metrics that differs, then writes the row and a `configuracion` row
of the `bitácora` naming each change by the metric's name, the threshold's label and the action
type's Spanish name, because a person reads it.

**Settings take effect on the next day run and the next decision.** `avanzar` reads them once
and detects on `src/centinela_api/agentes.py:with_thresholds(ctx, thresholds)`.
`avanzar` and the decision route hand the same thresholds to
`packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.use_thresholds(thresholds)`
before the day run or the resume, so the re-check before `Ejecutor` reads them too. The orchestrator is
never rebuilt, because its `InMemorySaver` holds the paused alerts. An owner decides as described
under decisions and roles, and an action type at `inform` cannot be approved.

## The tree's versions

**`api.arbol_versiones` holds every version of the client's tree as the move that made it**, keyed
by the client, `src/centinela_api/arboles.py:CLIENTE`, each with its `origen`, its parent, the agent
or the person, the alerts that drafted it, the base's `version` and hash, the hash of L0 and L1 and
the tree it yields, with the simulated day and the real time it was written. A version's id is the `Tree.version` the run walks and each alert stores. What
a move is, what refuses it and what the drafter returns is
[`../../packages/agents/arbol/AGENTS.md`](../../packages/agents/arbol/AGENTS.md#how-the-tree-grows).

| `origen` | Written when |
|---|---|
| `base` | a merged base replaced the one the newest version was built on |
| `expansion` | a move the drafter returned passed its criteria |
| `retiro` | a person retired an expansion |
| `descartada` | a draft the criteria refused, which carries its move and its evidence; or a move a merged base refuses, which carries its move and names, in `retira`, the row it drops, whose evidence stays on that row. No run walks it |

- **A merged base replays the client's moves.** `src/centinela_api/arboles.py:vigente(conn, grounds, growth, dia)`
  returns the newest version while the base it was built on is the base in the tree; otherwise it
  replays every `expansion` and `retiro` in order over the new base, writes a `base` row, and writes
  each move the new base refuses once as `descartada`, with a warning in the log and an `arbol` row
  of the `bitácora`. A move written so is never replayed on a later base and its evidence stays
  consumed, which departs from replaying every move on every base, because a refused move would
  otherwise be logged again on every day run, and a move that came back on a later base could share
  a node id the drafter has since given another split. Who merged a base is in the commit log, not
  in the row.
- **The tree grows at the start of each day run.** `src/centinela_api/arboles.py:del_dia(conn, dia)`
  takes an advisory lock, reads the version in force through `vigente`, hands the drafter the
  rejections of `api.rechazos` and every alert a row already names, and writes each move that
  passed as an `expansion` row with an `arbol` row of the `bitácora` under its agent. A refused
  draft is written once as `descartada`, with its `arbol` row and a warning, so its evidence is
  consumed and it is neither drafted again, replayed nor listed. It returns the newest version. A
  failure of the drafter is logged and the day runs on the version in force; a failure to read or
  rebuild the stored version is not caught there, and lands in the day run's `Detection phase
  failed` handler: an ERROR in the log with its traceback, a day that ends with no alerts, and a
  clock that has advanced.
- **`api.rechazos` keeps each rejection the classifier targeted**, with the alert's metric, the
  ids of the actions it rejected and the reason, written by the decision route after the resume;
  a rejection recorded with no paused graph has no target and keeps nothing.
- **An expansion is `active`, `retired` or `inactive`**, derived from the current tree: `inactive`
  is a move a merged base dropped, or one no longer live because a move it nests under was retired.
- **A person retires an expansion**, `src/centinela_api/arboles.py:retirar(conn, id, motivo, persona, dia, titulos)`:
  under the same lock, it refuses an expansion already retired or one not `active`, the retirement
  of the expansion's first node passes the criteria, then a `retiro` row and an `arbol` row of the
  `bitácora` under the person are written. It applies from the next day run; an alert already
  paused keeps the version it started on. The roles are
  `src/centinela_api/permisos.py:puede_retirar(persona)`'s, `analista` and `gerente`, the roles
  that configure, because a retirement changes what the agents decide, as a setting does.

## The clock

**The API owns the simulated clock**, the single row of `api.simulacion`. The first read seeds
it `CENTINELA_DIAS_DE_DEMO` days, thirty by default, before `centinela.fecha_corte()`;
`src/centinela_api/simulacion.py:avanzar(conn, dias)` adds days, and
`src/centinela_api/simulacion.py:sin_datos(conn, dias)` refuses with 409 a day past
`fecha_corte()`, because past it every day reads the same data. The day it moves replaces `fecha_corte()` (see
[`../../data/AGENTS.md`](../../data/AGENTS.md#the-simulated-clock)), and it reaches the
orchestrator as the argument of each run.

**One day run at a time.** A call to `/simulacion/avanzar` while a day run is in course is refused
with 409, because the second run would detect against earlier alerts the first has not
recorded, and one cause would raise two alerts.
`src/centinela_api/routers/simulacion.py:avanzar(dias, persona, conn)` takes the module's `asyncio.Lock`
before it moves the clock and frees it when the stream ends, fails or the client leaves; the
response's background task frees it for a stream that never starts.

**`avanzar` hands the day run every earlier alert** with its Spanish state, its severity, its
entity and, for one in `proposed`, its brief, `src/centinela_api/agentes.py:brief_of_alert(alerta)`:
its metric, its entity and its cause's sentence, for `Analista` to name as the same cause. A row
stored before `entidad` existed has none and covers nothing.

> **Decided, not built.** The API hands the day run the rejection reasons kept for each metric,
> each with the target the orchestrator classified it to. `api.rechazos` keeps them, and `avanzar`
> hands none.

## The alert lifecycle

**The contract and the database speak English statuses**: `new`, `analyzing`, `proposed`,
`approved`, `rejected`, `executed`, `merged`. The Spanish names stay at the edge: `estado=propuesta` on
`GET /alertas` is the brief's spelling, and
`src/centinela_api/ciclo_vida.py:ESTADO_A_STATUS` maps it.

**`src/centinela_api/ciclo_vida.py:transicionar(actual, siguiente)` refuses a transition
`TRANSICIONES` does not list**: `new` → `analyzing` → `proposed` → `approved` or `rejected`,
`approved` → `executed`, and `new` or `analyzing` → `merged`. `rejected`, `executed` and `merged`
are final, `src/centinela_api/ciclo_vida.py:FINALES`. A person's decision and the internal routes call it, and so do the two
paths the orchestrator drives. `avanzar` hands
`src/centinela_api/ciclo_vida.py:recorrer(estados)` the statuses the graph took the alert through,
read from its `transitions` by `src/centinela_api/agentes.py:status_path(alert_id, state)`, and
stores no alert whose path does not start at `new` or skips a transition. The resume after an
approval writes `executed` only after `transicionar` accepts it from `approved`. The database
keeps the last status, not the path.

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
- **A merge keeps one alert in view and loses nothing.** An alert whose run ends at `fin.unida` is
  stored `merged` with its `mergedInto` only while its target is still `proposed`, read with a row
  lock in the transaction that records it, and the target's `mergedAlerts` gains its summary,
  `src/centinela_api/agentes.py:merged_summary(alerta)`. So every alert of one cause points to the
  one that remains and none points to a merged alert. A target decided during the run refuses the
  merge, and the alert runs again on a fresh thread without that target among its candidates, so
  it reaches its own proposal and a person can decide it; its `alert` row names the refusal.
  `src/centinela_api/alertas.py:guardar(conn, alerta)` re-reads the row with a lock and keeps every
  stored `mergedAlerts` entry the alert it writes lacks, so a decision written while a day run adds
  a merged alert never drops it.
- **A detection the remaining alert absorbs never runs.** When `explicar.destino_nuevo` names a
  detection of the same day, `src/centinela_api/agentes.py:absorbed_alert(alert_id, detection, into, day_str)`
  stores it `merged` with its title, its pesos at risk under its detection's KPI call, and a cause
  that points to the alert that remains, and the run skips it; the run hands over only a
  detection still to run. `GET /alertas` lists the alert that remains, and its detail carries each merged one's
  detection and evidence. Its pesos at risk stay its own, because two detections of one cause
  would count the same pesos twice.

## Decisions and roles

**A person signs in, and every route reads the person from the token.** The profiles are
`CENTINELA_USUARIOS` in the root `.env`
([`../../CONEXION_WEB_API.md`](../../CONEXION_WEB_API.md#signing-in) lists them), each `clave` a
PBKDF2-SHA256 hash at the iterations `ITERACIONES` names, written by
`python -m centinela_api.auth hash`, because that file is public. A malformed list stops the API at
import, so a typo never signs everyone out silently.
`src/centinela_api/auth.py:verificar(correo, clave)` matches the email in any case and hashes
against a dummy of the same cost when the email is unknown, so neither the time nor the message
tells which half failed. `src/centinela_api/auth.py:emitir(persona, ahora)` signs the email and an
eight-hour expiry with HMAC-SHA256, and `src/centinela_api/auth.py:leer(token, ahora)` checks the
signature and the expiry and re-reads the person from the profiles, so removing a profile ends its
sessions.

**The signing key is never versioned.** A key in the public `.env` would let anyone with the
repository sign a `gerente` token without a password. `AUTH_SECRET_KEY` comes from `.env.local`;
without it, `src/centinela_api/config.py` draws a random key per process, and every session ends
when the API restarts. A stable key, for a demo that restarts, goes in `.env.local`.

**Sign-out is the client's.** "Salir" drops the browser's copy; the token stays valid until it
expires, and nothing throttles `/auth/login`. Full enterprise authentication, revocation included,
is out of scope ([`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md)).

**Who decides is checked before the decision.**
`src/centinela_api/permisos.py:puede_decidir(conn, persona, alerta)` lets the `gerente` decide every
alert, and a `lider_proceso` the alerts whose metric its `area` owns, as
`src/centinela_api/permisos.py:area_que_decide(conn, metric)` reads the owner from the settings. A
metric with no owner, or one no `lider_proceso` profile holds, leaves the alert to the `gerente`,
because no one else could act on it. An `auditor` gets a 403 saying auditing reads, anyone else "Esta alerta la decide" and the area, or "la gerencia": the request is
valid, the person may not make it. `src/centinela_api/permisos.py:vista(conn, persona, alerta)` adds
`decidedBy`, the area or `Gerencia`, and the person's `canDecide` to every alert returned, so the
screen decides no permission; `src/centinela_api/alertas.py:guardar(conn, alerta)` strips both,
because they belong to the request. Then `src/centinela_api/decisiones.py:aplicar(alerta, decision, autonomia)`
requires the alert in `proposed` (409), a rejection to carry a reason (422), and an approval or an
edit to name one of the alert's actions (422) whose type the settings do not set to `inform`
(422 "Este tipo de acción solo informa"). "Ejecuta" is refused for every action type, with 422 on
saving the settings, because the challenge keeps every action at `Propone`
([`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its responsible AI section).

**A decision is recorded only where it can act, and committed before anything resumes.**
`src/centinela_api/routers/alertas.py:decidir(id, decision, persona, conn)` answers 409 "Esta alerta
está procesando otra decisión" while another decision on the same alert is resuming its graph, and
409 "El análisis de esta alerta ya no está en pausa: no puede reanudarse" to an approval, an edit or
a request for changes when
`packages/agents/centinela_agents/orchestrator.py:CentinelaOrchestrator.is_awaiting_decision(alert_id)`
is false, after a restart or a resume that failed midway, so no decision is recorded that nothing
would carry out. A rejection is still recorded there, without a resume, because it runs nothing and
otherwise the alert would wait forever. The decision transaction re-reads the alert with a row lock
and runs `aplicar` on it, so two concurrent decisions cannot both pass, and commits the alert and
its `bitácora` row, whose actor is the person's name and role, before the orchestrator resumes, so
no action runs without a recorded decision; an approval or an edit, with every stored parameter, resumes into `Ejecutor`,
and a rejection resumes to close the graph.

**A `request_changes` carries a reason, and is capped at one per alert**, because a person who
still disagrees after one new proposal has the decision in hand: an edit says what to change and a
rejection says why, and both close the alert. `aplicar` refuses a blank reason (422) and a second
request (409 "Ya se pidieron cambios una vez"). The alert stays `propuesta` with
`changesRequested` set while the decision route resumes the graph, `Estratega` proposes again
with the reason among the rejection reasons it reads, and `src/centinela_api/routers/alertas.py:_reproponer(conn, alerta, motivo, ajustes, dia)`
stores the new actions with a `proposal` row of `Estratega` and the `evidence` rows of the new
queries, only while the alert is still `proposed`. When the resume fails or returns no action,
the alert keeps its previous actions and a `proposal` row records the failure: a graph still at
the gate that never consumed the request gives `changesRequested` back, and a graph the failure
left off the gate leaves only the rejection, which the row says.

> **Decided, not built.** The rules below, where the code differs as each one says.

- **An edit keeps the keys of the action's `parameters`, adding none and dropping none**, because
  `Ejecutor` passes them unchanged. `aplicar` merges the edit into them, so a new key passes.

**Personal data reaches the models unmasked.** `src/centinela_api/masking.py:mask_dict_for_model(data)`
replaces client and vendor ids and names with a hash-suffixed placeholder, the same for the same
input, but no route calls it, and `mask_text_evidence` replaces only the pairs it is handed. It
costs the challenge's Ley 1581 requirement on every model call, and is paid when the data a model
reads goes through it, in this level or in `packages/tools`, whose page owns masking.

## The inbox totals

**The API computes the inbox totals**: `src/centinela_api/resumen.py:calcular(conn)` runs three
statements over `api.alertas` where `status` is `proposed`, in one `REPEATABLE READ` snapshot so a
day run cannot split them, and `GET /bandeja/resumen` serves them.
They are pesos at risk and recoverable per month, each a sum, and the count of decisions pending.
They are sums over alerts rather than a `v_*` view, so each figure's query is recorded in
`api.consultas` with the source `alertas`, its SQL and the simulated day, under a `queryId`
derived from the SQL, the day and the value: the same value read again records nothing new, and
`/consultas/{queryId}` opens the query with a Spanish description of the sum. The screen computes
none.

## The `bitácora`

**`api.bitacora` is append-only**: `src/centinela_api/bitacora.py:registrar(conn, alerta_id, tipo, actor, detalle, dia_simulado, query_id, figures)`
inserts, and no code updates or deletes a row; no grant enforces it. Each row carries its type,
its actor, an agent or a person with name and role, its detail, the simulated day and the real
time, the alert it belongs to, which a chat question asked from no alert leaves empty, and the
figures its detail's placeholders point to.

| Type | Written by |
|---|---|
| `alert` | `avanzar`, for each alert the orchestrator returns, with its title's figures, and for each merge, under `analista`, naming the alert that remains; `POST /interno/alertas` |
| `evidence` | `avanzar`, one row per `kpi_consultar` a leaf ran, the KPI's `etiqueta` and day as the detail and its `queryId`, and `_reproponer` for each query a new proposal added; `PUT /interno/alertas/{id}/causa` |
| `proposal` | `_reproponer`, for a new proposal after a request for changes or its failure; `PUT /interno/alertas/{id}/propuesta` |
| `decision` | a person's decision |
| `action` | `POST /interno/alertas/{id}/ejecutar` |
| `result` | the resume after an approval: the executed action, or why it was not executed, `src/centinela_api/routers/alertas.py:no_ejecutada(fin, dia)` |
| `question` | `/chat`, the person's question with its email addresses and keys masked |
| `evidence`, from the chat | `/chat`, one row per query the chat ran |
| `answer` | `/chat`, the text of an answer with its figures and its first figure's `queryId` |
| `costo` | `/chat`, one per model step, through `src/centinela_api/bitacora.py:registrar_costo(conn, alerta_id, actor, detalle, dia_simulado)`; `GET /bitacora` never serves it |
| `refusal` | `/chat`, a question the screen flagged, one outside the chat's use, or one asking to act |
| `configuracion` | `PUT /configuracion`, the person who saved and each change, with no alert |
| `arbol` | the growth of a day, under the agent whose move it is, a move refused or dropped by a merged base, and a retirement, under the person, each with no alert |

On the path that runs, a day's alert lands with its `alert` row, which cites the KPI's `queryId`,
and one `evidence` row per query its leaves ran, so every figure of the alert resolves to the SQL
that returned it; an approval adds its `decision` and `result`. The graph's first proposal leaves
no row of its own.

## Rules of this level

- **No decision, no action.** The API resumes an alert past the approval interrupt only after the
  decision is committed with its role. *No gate holds this.*
- **The API's state lives in its own schema `api`**, created by `sql/01_esquema.sql` with
  `IF NOT EXISTS`, never in the dataset's `centinela` schema. The file runs again on a database it
  built before: its `ALTER`s on `api.bitacora` give the table the shape a new one has, so there is
  no migration tool. *No gate holds this.*

- **An alert carries its cost**: the day run stores the `cost` the orchestrator counts per alert
  in `api.alertas.costos`. The decision route writes no cost, so a resume's model calls are not
  added. *No gate holds this.*
- **Timeouts and retries are explicit**, as
  [`../../packages/agents/AGENTS.md`](../../packages/agents/AGENTS.md#how-a-step-runs) states them,
  and "not enough evidence" is a valid response, not an error. A failed alert of a day is logged
  and the day goes on. *No gate holds this.*

> **Decided, not built.** The rule below, where the code differs as it says.

- **The project is a uv project**, with its lockfile beside this page, as `packages/agents` and
  `packages/tools` are. It is a setuptools package installed with pip.
