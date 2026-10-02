# apps/api: the API, the clock and the log

<<<<<<< HEAD
This level is the only door into Centinela: the web, the jury and any script reach it through
the public endpoints; `packages/agents` reaches it through internal endpoints. It owns the alert
lifecycle, the simulated clock, the `bitácora`, and the interface contract. This page states the
decisions the code is written against. The endpoints it serves are
=======
This level is the only door into Centinela: the web, the jury and any script reach the agents
through it. It holds the skeleton the endpoints are built on: FastAPI, the API's own schema, the
alert lifecycle and the `bitácora`, not yet wired to `packages/agents` or `packages/tools`. This
page states the decisions the code is written against. The endpoints it must serve are
>>>>>>> 237624b (apps/api now owns a Postgres schema, the alert lifecycle and the bitácora, so the six minimal endpoints run for real while Vigía, Analista, Estratega and Ejecutor are still unbuilt.)
[`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its minimal API section.

## Decisions

- **Python, FastAPI and Pydantic**, REST plus SSE streaming for the chat and for agent progress.
<<<<<<< HEAD
- **The API owns the simulated clock.** Advancing it moves the simulated day that replaces
  `fecha_corte()` (see [`../../data/AGENTS.md`](../../data/AGENTS.md), its clock section).
- **The API owns the alert lifecycle: it validates every transition and persists it**, and
  refuses one the lifecycle does not list. The orchestrator proposes the transitions an agent
  causes, because it is the only part that sees an agent finish; the API proposes the ones a
  person causes. The record is the API's, because it is the only part with storage and the only
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
- **One day run at a time.** A call to `/simulacion/avanzar` while a day run is in course is
  refused with 409, because the second run would detect against earlier alerts the first has not
  recorded yet, and one cause would raise two alerts.
- **The API hands each run what the orchestrator cannot read**: the metric, entity, severity and
  state of every earlier alert, and the rejection reasons kept for the alert's metric. It keeps
  each reason with the target the orchestrator classified it to, the metric and the entity.
- **The API checks a decision before it resumes an alert**: the role may make it, a rejection
  carries a reason, an edit keeps the keys of the action's `parameters`, adding none and dropping
  none, because `Ejecutor` passes them unchanged, and a `request_changes` carries a reason and is
  refused on an alert that already had one, because the return to `Estratega` is capped at one.
- **`request_changes` adds no state to the lifecycle.** The alert stays `propuesta` while
  `Estratega` proposes again, and its reason joins the rejection reasons `Estratega` reads, because
  a person asking for another proposal has neither approved nor rejected the alert.
- **The API stores the graph's checkpoints in its own schema** and injects the checkpointer into
  the graph, because no agent opens a database connection.
- **The API owns the `bitácora`**, which is append-only: alert, evidence, proposal, decision,
  action and result, each with who and when. Nothing updates or deletes a row of it.
- **Roles decide who may approve.** Full enterprise authentication is out of scope; roles are not.
=======
  `centinela_api/sse.py:flujo()` turns an async generator of `(event, model)` pairs into
  `text/event-stream`.
- **The HTTP contract is English and camelCase**, mirroring `apps/web/src/api/types.ts` field for
  field: `centinela_api/modelos.py` is the source, and `Esquema`'s `alias_generator` emits
  `pesosAtRisk` from `pesos_at_risk` so the web's fetch client can replace its simulated one without
  a reshape.
- **The lifecycle's Spanish names stay at the edge.** `estado=propuesta` on `GET /alertas` is the
  brief's spelling; `centinela_api/ciclo_vida.py:ESTADO_A_STATUS` maps it to the English `status`
  (`proposed`) that the contract, the database and `ciclo_vida.transicionar()` use everywhere else.
- **The API owns the simulated clock**, in `api.simulacion`, a single-row table. Advancing it moves
  the simulated day that replaces `fecha_corte()` (see
  [`../../data/AGENTS.md`](../../data/AGENTS.md), its clock section); the first read seeds it from
  `centinela.fecha_corte()`.
- **The API owns the alert lifecycle and persists it**: `nueva` → `en análisis` → `propuesta` →
  `aprobada` or `rechazada` → `ejecutada`. A transition the lifecycle does not list is refused,
  enforced in code by `ciclo_vida.transicionar()`.
- **Approving stops at `aprobada`.** Reaching `ejecutada` is `Ejecutor` running the action, which
  this skeleton does not build yet; `POST /alertas/{id}/decision` never executes anything itself.
- **Roles decide who may approve**, read from an `X-User-Role` header against
  `config.ROLES_CON_DECISION` (`gerente`, `lider_proceso`). Full enterprise authentication is out of
  scope, so there is no login yet: `X-User-Name` carries the acting person's display name,
  percent-encoded, because a raw header is ASCII-only and Colombian names are not.
- **This skeleton does not call `packages/agents` or `packages/tools` yet.**
  `POST /simulacion/avanzar` only moves the clock and ends with no new alerts; `POST /chat` always
  answers "no tengo evidencia suficiente". Wiring in `Vigía`, `Analista`, `Estratega` and `Ejecutor`
  is the next task, and `api.alertas` has no writer until then besides a decision on an
  already-seeded alert.
>>>>>>> 237624b (apps/api now owns a Postgres schema, the alert lifecycle and the bitácora, so the six minimal endpoints run for real while Vigía, Analista, Estratega and Ejecutor are still unbuilt.)

## Rules of this level

- **No decision, no action.** The API never resumes an alert past the approval interrupt without a
  recorded decision from a role allowed to make it. *No gate holds this.*
- **The API's state lives in its own schema** (`api`, in the same Postgres database
  `data/docker-compose.yml` already runs): alerts, decisions and the log, never in the dataset's
  `centinela` schema.
- **An alert carries its cost**: tokens and model calls are recorded per alert, in `api.alertas.costos`,
<<<<<<< HEAD
  a column reserved for a list. No code writes it until an agent runs, and it is not in the public
  `Alert` contract because `apps/web/src/api/types.ts` does not carry it.
- **Timeouts and retries are explicit**: `packages/agents` handles these; the API returns what it
  receives or times out waiting.
- **The `bitácora` is append-only in code, not yet by a database grant**: nothing in this level
  issues `UPDATE` or `DELETE` against `api.bitacora`. *No gate holds this.*
- **Sensitive data is masked before reaching models**: `masking.py` anonymizes names and IDs in
  data sent to `packages/agents`. The bitácora stores unmasked. *No gate holds this.*
- **Each agent has one job**: `Vigía` creates, `Analista` explains, `Estratega` proposes,
  `Ejecutor` executes (after approval). No agent can overwrite another's output.

## Tests

Run from this directory:

| Command | What it does |
|---|---|
| `pytest tests/test_flujo_agentes.py` | Unitario: endpoints exist, auth works, masking is deterministic (9 tests) |
| `pytest -m integracion` | Integración: full flow with real BD (requires DSN_ADMIN, data/docker-compose.yml running) |

Tests use mocks for quick feedback (`test_flujo_agentes.py`) and real Postgres for end-to-end
(`test_api_integracion.py`, `test_ciclo_vida.py`).

## Example: Vigía detects, Analista explains, Estratega proposes, human decides

```bash
# 1. Vigía creates an alert (POST /interno/alertas)
curl -X POST http://localhost:8000/interno/alertas \
  -H "X-Agent: vigia" -H "X-Agent-Key: your-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "high",
    "metric": "margen_pct",
    "title": {"text": "Margin fell 6 points", "figures": []},
    "pesosAtRisk": {"value": 42000000, "unit": "COP", "queryId": "q_margin"},
    "confidence": {"level": "high", "assumptions": []},
    "simulatedDate": "2026-01-15"
  }'
# Returns: Alert{id: "alerta_abc123...", status: "new", ...}

# 2. Analista ingests cause (PUT /interno/alertas/{id}/causa)
curl -X PUT http://localhost:8000/interno/alertas/alerta_abc123/causa \
  -H "X-Agent: analista" -H "X-Agent-Key: your-secret" \
  -H "X-Cost-Json: {\"agent\":\"analista\",...}" \
  -d '{
    "cause": {
      "kind": "identified",
      "sentence": {"text": "Supplier X raised cost", "figures": [...]},
      "evidence": [...]
    }
  }'
# Returns: Alert{status: "analyzing", cause: {...}}

# 3. Estratega proposes actions (PUT /interno/alertas/{id}/propuesta)
curl -X PUT http://localhost:8000/interno/alertas/alerta_abc123/propuesta \
  -H "X-Agent: estratega" -H "X-Agent-Key: your-secret" \
  -d '{
    "actions": [{
      "id": "action_raise_price",
      "title": {"text": "Raise price 3%", ...},
      "type": "price_change_draft",
      "impact": {"figure": {...}, "period": "month"},
      ...
    }]
  }'
# Returns: Alert{status: "proposed", actions: [...]}

# 4. Human approves via public endpoint (POST /alertas/{id}/decision)
curl -X POST http://localhost:8000/alertas/alerta_abc123/decision \
  -H "X-User-Name: Juan%20Pérez" -H "X-User-Role: gerente" \
  -d '{"kind": "approve", "action_id": "action_raise_price"}'
# Returns: Alert{status: "approved"}

# 5. Ejecutor executes (POST /interno/alertas/{id}/ejecutar)
curl -X POST http://localhost:8000/interno/alertas/alerta_abc123/ejecutar \
  -H "X-Agent: ejecutor" -H "X-Agent-Key: your-secret" \
  -d '{
    "action_id": "action_raise_price",
    "status": "success",
    "result": "Draft price change created and sent to approvals"
  }'
# Returns: Alert{status: "executed", executedAction: {...}}

# 6. Audit trail (GET /bitacora)
curl http://localhost:8000/bitacora?alertId=alerta_abc123
# Returns: LogEvent[]{
#   {type: "alert", actor: {kind: "agent", agent: "vigia"}, detail: "..."},
#   {type: "evidence", actor: {kind: "agent", agent: "analista"}, detail: "..."},
#   {type: "proposal", actor: {kind: "agent", agent: "estratega"}, detail: "..."},
#   {type: "decision", actor: {kind: "person", name: "Juan Pérez", role: "gerente"}, detail: "..."},
#   {type: "action", actor: {kind: "agent", agent: "ejecutor"}, detail: "..."}
# }
```
=======
  a column reserved for a list of `packages/agents/src/centinela_agents/esquemas.py:RegistroCosto`.
  No code writes it until an agent runs, and it is not in the public `Alert` contract because
  `apps/web/src/api/types.ts` does not carry it.
- **Timeouts and retries are explicit**, and "not enough evidence" is a valid response, not an error.
- **The `bitácora` is append-only in code, not yet by a database grant**: nothing in this level
  issues `UPDATE` or `DELETE` against `api.bitacora`. *No gate holds this.*
>>>>>>> 237624b (apps/api now owns a Postgres schema, the alert lifecycle and the bitácora, so the six minimal endpoints run for real while Vigía, Analista, Estratega and Ejecutor are still unbuilt.)

## Commands

Run from this directory, with the Postgres from [`../../data/AGENTS.md`](../../data/AGENTS.md)
already up and `data/sql/01..03` already applied:

| Command | What it does |
|---|---|
| `pip install -e ".[dev]"` | installs the package and test dependencies |
| `psql "$DSN_ADMIN" -f sql/01_esquema.sql` | creates the `api` schema; safe to re-run, nothing drops |
| `uvicorn centinela_api.main:app --reload` | runs the API on `http://127.0.0.1:8000` |
<<<<<<< HEAD
| `pytest tests/test_flujo_agentes.py` | quick unit tests (no DB needed) |
| `pytest -m integracion` | integration tests (requires DB up and DSN_ADMIN set) |

**Setup**:

1. Copy `.env.example` to `.env` and fill in:
   - `DSN_ADMIN=postgresql://centinela:centinela@localhost:5432/centinela` (from `data/docker-compose.yml`)
   - `AGENT_SECRET_KEY=your-secret-for-agents-prod` (used to authenticate `/interno/*` endpoints)

2. Start database: `docker-compose -f data/docker-compose.yml up -d`

3. Create API schema: `psql "$DSN_ADMIN" -f sql/01_esquema.sql`
   (Or via Docker if no local `psql`: `cat sql/01_esquema.sql | docker exec -i centinela-db psql -U centinela -d centinela`)

4. Install and run:
   ```bash
   pip install -e ".[dev]"
   uvicorn centinela_api.main:app --reload
   ```

**Swagger UI**: `http://127.0.0.1:8000/docs` calls every endpoint from the browser. Try:
- `GET /alertas` (returns empty until Vigía creates one)
- `POST /interno/alertas` (create test alert; requires `X-Agent: vigia` + `X-Agent-Key`)
- `GET /bitacora` (see audit log)

## Key files and modules

| File | Purpose |
|---|---|
| `src/centinela_api/main.py` | FastAPI app definition and router imports |
| `src/centinela_api/modelos.py` | Pydantic models: Alert, Decision, AgentAlertInput, etc. (HTTP contract) |
| `src/centinela_api/ciclo_vida.py` | State machine: transitions from new → analyzing → proposed → approved/rejected → executed |
| `src/centinela_api/masking.py` | Data anonymization: masks cliente names and IDs before models see them |
| `src/centinela_api/routers/alertas.py` | Public endpoints: GET /alertas, GET /alertas/{id}, POST /alertas/{id}/decision |
| `src/centinela_api/routers/interno.py` | Internal endpoints: POST/PUT /interno/alertas/* (agent gates) |
| `src/centinela_api/routers/simulacion.py` | POST /simulacion/avanzar (move clock, emit events) |
| `src/centinela_api/routers/chat.py` | POST /chat (currently stub; will call packages/agents) |
| `src/centinela_api/routers/bitacora.py` | GET /bitacora (audit trail) |
| `src/centinela_api/db.py` | Connection pooling and dependency injection |
| `src/centinela_api/config.py` | Environment variables: DSN_ADMIN, AGENT_SECRET_KEY, ROLES_CON_DECISION |
| `sql/01_esquema.sql` | Tables: api.simulacion, api.alertas, api.bitacora |
| `tests/test_flujo_agentes.py` | Unit tests for endpoints and masking (uses mocks) |

## What `packages/agents` needs from this API

1. **POST /interno/alertas** endpoint exists, ready to receive `AgentAlertInput` (created by Vigía orchestrator)
2. **PUT /interno/alertas/{id}/causa**, **propuesta**, **ejecutar** endpoints ready to receive results from each agent
3. **Masking is built in**: agents receive masked client data; send to LLMs only anonymized data
4. **State machine enforced**: the API never allows invalid transitions; agents don't need to track state
5. **Bitácora records everything**: costs, latencies, and decisions are all logged for audit
6. **X-Agent-Key authentication**: set this in production; unit tests use "insecure-dev-key"
7. **Swagger/OpenAPI at /docs**: teams can explore the contract live

## What `apps/web` needs from this API

1. **Public endpoints** (`/alertas`, `/alertas/{id}`, `/alertas/{id}/decision`, `/chat`, `/bitacora`) are ready
2. **All responses are camelCase** (pesosAtRisk, not pesos_at_risk) for direct use in TypeScript
3. **SSE streaming** for `/simulacion/avanzar` and `/chat` — the web client receives live events
4. **User roles** (`X-User-Role: gerente|lider_proceso`) control who can approve
5. **Open Swagger UI at /docs** for live testing

## Decisions deferred to `packages/agents`

- How to structure the orchestrator graph (LangGraph, custom, etc.)
- Which models for each step (claude-opus for Analista/Estratega, claude-haiku for routing, etc.)
- How to handle retries and timeouts (circuit breaker logic)
- How to embed policies in pgvector and retrieve them
- Whether to call agents in-process or as a microservice
=======
| `pytest` | the unit tests, always; `pytest -m integracion` also needs this level's schema applied and `DSN_ADMIN` set |

`DSN_ADMIN` is a Postgres connection string with write access; copy `.env.example` to `.env` to get
the one `data/docker-compose.yml` creates. Without a local `psql` client, the schema command becomes
`cat sql/01_esquema.sql | docker exec -i centinela-db psql -U centinela -d centinela` (PowerShell:
`Get-Content sql/01_esquema.sql -Raw | docker exec -i centinela-db psql -U centinela -d centinela`),
run against the container `data/docker-compose.yml` starts.

With the server running, `http://127.0.0.1:8000/docs` is a Swagger UI that calls every endpoint
from the browser; `GET /alertas` and `POST /alertas/{id}/decision` need a row in `api.alertas` to
act on, since nothing creates one until `Vigía` exists.
>>>>>>> 237624b (apps/api now owns a Postgres schema, the alert lifecycle and the bitácora, so the six minimal endpoints run for real while Vigía, Analista, Estratega and Ejecutor are still unbuilt.)
