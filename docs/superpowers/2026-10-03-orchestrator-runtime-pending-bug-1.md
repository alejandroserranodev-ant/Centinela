# Bug spec 1: the orchestrator's runtime, as `packages/agents/AGENTS.md` states it

**Status:** pending its plan. **Runs after** spec 5, `current-kpis-in-kernel`, and **before**
spec 3, `tree-expansion`, because spec 3 builds on a day run, a cost and an `AgentStep` that this
spec writes. **Depends on:** spec 2, `decision-tree`, for the interpreter it completes; spec 4,
`kpi-kernel`, for `kpi_consultar`, which returns rows with their query, and for the ISO 22400-2
`unidad` of each metric; spec 5 for the base KPIs the detection reads, with their
`pesos_en_riesgo` and `pedidos_pendientes` columns.

## Why

`packages/agents/AGENTS.md` states the orchestrator's design, and its interpreter implements the
walk, the validator, the gate and the resume as stated. The rest of the page states a runtime that
no code holds, and only `cost` and the attempts of a failure are marked as missing:

| The page states | The code holds |
|---|---|
| the day run checks each detection against the earlier alerts, orders the alerts by `pesosAtRisk`, and runs them in series | `centinela_agents/walk.py:detect(ctx, day)` only: no check, no order, no series |
| the orchestrator names an alert by metric, entity and simulated day | `centinela_agents/graph.py:start_alert(graph, detection, *, alert_id, day, ...)` takes the id from its caller |
| `detection` carries `cifra`, `regla`, `fuente_umbral`, severity, `tramo` and `pesos_en_riesgo` | `start_alert` writes `metric`, `entity`, `path` and `row`; nothing computes a severity |
| the chat goes to `Analista`/`responder_chat` on its own route | the decision is in `centinela_agents/schema.py:AGENT_DECISIONS` and nowhere else |
| a transition `apps/api` refuses ends that alert's run | nothing receives a refusal |
| a model call is retried once, an alert has a token cap, each call adds to `cost` | a leaf fails on its first exception; no cap, no `cost` |
| an `AgentStep` when an agent's node starts and ends; one Langfuse trace per alert | neither |
| `Ejecutor` receives the approved action and the decision, nothing else | it also receives `alert_id`, which the idempotency of an action needs |
| the classifier reads the reason, the `Cause` and the actions, each placeholder replaced by its figure | it reads the whole state |

One gap is in the design, not only in the code: **no file defines severity.** `metricas.yaml`
holds no rule that makes an alert `critical`, `high`, `medium` or `low`, yet the order of a day and
the rule that an alert is raised again only when its severity rises depend on it.
`docs/guide/chapters/status.md` lists the tree's growth as the only pending design of
`packages/agents`, so it does not show any of this.

## Decisions

### Severity and `tramo` are data of `metricas.yaml`

- **Each metric gains a `severidad` block**, written by a person, because a severity is a business
  rule and an agent states no rule that a document does not hold. The block has a `por_defecto` and
  an optional list of `niveles`, read from `critical` down. The first level whose conditions all
  hold on the KPI row wins, and if none holds the alert takes `por_defecto`:

  ```yaml
  severidad:
    por_defecto: { nivel: high, fuente: "supuesto: incumplir una regla escrita es high" }
    niveles:
      - nivel: critical
        fuente: "OPE-POL-007 §2"
        cuando:
          - { columna: cobertura_dias, op: "<", umbral: 5 }
          - { columna: pedidos_pendientes, op: ">", umbral: 0 }
  ```

  A condition is atomic, as a node of the tree is: one column of the metric's KPI, one operator
  from the tree's list, and either a number or `{ columna: ... }` as `umbral`. **`por_defecto` is
  `high` for every metric**, because breaking a written rule is the reason an alert exists, and
  no document grades a plain breach lower. That default is an assumption, stated in its `fuente`.
- **Only a document raises a level above the default.** The policies state one such case:
  `cobertura_dias` under 5 days with orders pending dispatch is `crítico` (OPE-POL-007 §2). The
  escalation of FIN-POL-004 §4 names who acts on each tranche but no severity, so it is left to
  the person who writes `saldo_vencido`'s block to decide whether `tramo_4`, escalated to
  `Dirección Financiera`, is `critical`. The person records the reading in `fuente`, and the
  decision is made in the pull request, never by an agent.
- **`tramos` becomes structured**, because `detection` carries a `tramo` that code must compute:

  ```yaml
  tramos:
    fuente: "FIN-POL-004 §4"
    columna: max_dias_vencido
    niveles:
      - { tramo: tramo_1, desde: 1, hasta: 15 }
      - { tramo: tramo_2, desde: 16, hasta: 30 }
      - { tramo: tramo_3, desde: 31, hasta: 60 }
      - { tramo: tramo_4, desde: 61 }
  ```

  A level of `severidad` may name a `tramo` instead of `cuando`.
- **The validator checks both blocks**: shape, operators, that each column is one the catalogue
  holds for the metric's KPI, that the tranches neither overlap nor leave a gap, and that every
  `fuente` is non-empty. A metric of `metricas.yaml` with no `severidad` is refused, as one with no
  L3 branch is.
- **`pedidos_pendientes` is a column of the cobertura KPI that spec 5 builds** from dates on the
  simulated day, because `pedidos.estado`, which spec 4 marks `fuga`, cannot say which orders were
  pending on that day.

### The detection is complete, and code computes it

- **`walk.py:detect(ctx, day)` returns a complete detection**, because `Vigía`'s `detectar` is code:
  - `cifra` is the `Figure` of the column the last KPI node passed on `si` reads: its value, its
    unit, and the `queryId` of the reading.
  - `regla` is the metric's `umbral_alerta` and `fuente_umbral` is the metric's `fuente_umbral`.
  - severity and `tramo` come from the two blocks above.
  - `pesos_en_riesgo` is the `Figure` of the KPI row's `pesos_en_riesgo` column, in `COP`, with the
    same `queryId`.

  The model computes no field.
- **The reader returns its query with its rows.** `KpiReader` becomes a function of a metric and a
  day that returns a reading: `query_id`, `sql` and `rows`, as `kpi_consultar` returns them
  (spec 4). Each reading joins the alert's `queries`, because every figure travels with its query.
- **The detection reads `pesos_en_riesgo` from the column every base KPI outputs** (spec 5), so
  the exposure has one definition and the interpreter computes none. The package's tests use a
  stub reader that holds the column.
- **The unit of `cifra` maps the metric's ISO 22400-2 `unidad` (spec 4) to `FigureUnit`** of
  `apps/web/src/api/types.ts`. A `unidad` with no mapping refuses the base, because a figure with
  no unit cannot be shown.

### The day run is a generator the caller drives

- **The alert id is a function of metric, entity and day**,
  `centinela_agents/graph.py:alert_id(metric, entity, day)`: `alr-` followed by the first 16 hex
  digits of the SHA-256 of the canonical JSON `[metric, entity, day]`. It is a hash, because entity
  values hold spaces and accents, while the id travels in URLs, in thread ids and in the
  `bitácora`. A day run twice proposes the same ids, and `apps/api` refuses the second.
  `start_alert` stops taking an id.
- **`centinela_agents/day.py:run_day(...)` takes** the simulated day, the earlier alerts (metric,
  entity, severity, state), the rejection reasons kept by metric, and the tree version. It
  detects, drops the detections the earlier alerts cover, orders the rest, and runs each alert's
  graph in series up to the gate or an end.
- **Coverage by earlier alerts**: a detection is dropped when an earlier alert has the same metric
  and entity, whatever its state, unless its severity is strictly higher than the highest of those
  alerts. This is the rule `Vigía`'s ceiling already states, now written as code.
- **Order**: `pesos_en_riesgo` from the largest, then severity from `critical` down, then alert
  id. A null `pesos_en_riesgo` sorts last, because an unmeasured exposure cannot claim the inbox
  first.
- **The caller drives the run, so nothing calls back up the chain.** `run_day` yields one result
  per alert: its final state, the transitions it proposes, and its log events. The caller
  (`apps/api`) records the result and sends back a verdict, the transitions it accepted.
  - A refused transition ends that alert: the run does not resume it, and the `unida` it proposed
    for a later alert does not apply.
  - An accepted `unida` for a later alert removes that alert from the run, because it was absorbed
    before its turn.

  `resume(graph, alert_id, decision)` follows the same contract for one alert. A generator, not an
  injected callback, because the dependency rule of the root page allows `apps/api` to call
  `packages/agents` and forbids the reverse.

### The chat is a function, not a node

- **`centinela_agents/chat.py:answer(question, anchored_alert, ...)` calls the leaf
  `analista`/`responder_chat` directly**, with `skills/analista/contrato.md`. Spec 2 keeps the
  chat off the tree, and the validator refuses a leaf that `detectar.raiz` does not reach. The
  answer carries a `Sentence`, its queries and its own cost, and it touches no alert's state.
- **A failed chat answer is a fixed text by failure**, as `explicar`'s fallback is: "No pude
  responder: " followed by the cause of the matching row of the `REASONS` table, so a person never
  reads a model's error.

### A model call goes through the interpreter's wrapper

- **A leaf receives a `model` function from the interpreter instead of calling Ollama itself.**
  `LeafFunction` becomes `(given, model) -> update`. The host injects the client into
  `compile_tree` and `answer`, and the wrapper applies to every call:
  - the timeout per call;
  - one retry on a timeout, a connection error or an output its schema refuses;
  - the addition of Ollama's `prompt_eval_count`, `eval_count` and one call to `cost`, under the
    leaf's agent;
  - the check of the alert's token cap after the call. Once the cap is reached, every later call
    on that alert raises `TokenCapReached` at once, so each model step left takes its fallback.

  The wrapper sits in the interpreter, because "how a step runs" belongs to the interpreter and a
  leaf with several calls would otherwise retry each one by its own rule.
- **The state gains `cost`**, by agent: prompt tokens, output tokens and calls, merged by a reducer
  across the nodes. **A failure gains `attempts`.** The paragraph of the page that says the code
  has neither is deleted.

### Steps and traces leave through the graph's stream

- **Each leaf node writes an `AgentStep` with LangGraph's stream writer when it starts and when it
  ends**, and `run_day`, `resume` and `answer` pass those steps on in the order they come. The
  `description` is a fixed Spanish text per agent and decision, kept in code beside
  `LEAF_OUTPUTS`, because a step's label is a fixed value, not a model's output. The caller streams
  the steps on. A stream rather than a sink, for the dependency rule above.
- **Tracing is a callback handler the host injects**, Langfuse's in production and none in tests.
  The trace id is the alert id for an alert's graph and its resume, the day for detection, and a
  question id for the chat. Without a handler, every run still completes, because a trace observes
  and never decides.

### The two small discrepancies

- **`Ejecutor`'s input keeps `alert_id`, and the page says so**, because an action is keyed by alert
  and action so that a second run has no effect.
- **The classifier's input is built as `skills/orquestador/contrato.md` declares it**: `motivo`,
  `causa` and `acciones`, each placeholder replaced by its figure, in code, from the state. Before,
  it received the whole state.

## Pages this spec changes

| Page | Change |
|---|---|
| `data/metricas.yaml` | a `severidad` block on every metric; `tramos` structured on `saldo_vencido` |
| `data/AGENTS.md`, "Rules of this level" | a sentence: a metric's severity is its `severidad` block, whose default is `high` by stated assumption and whose higher levels each cite a document |
| `packages/agents/AGENTS.md`, `Vigía` | the output names where severity and `tramo` come from; the tools read readings with their query |
| `packages/agents/AGENTS.md`, `Ejecutor` | its input names `alert_id`, and the reason |
| `packages/agents/AGENTS.md`, "The orchestrator interprets the tree" | its input from `apps/api` and its output as a generator with a verdict sent back; the alert id function |
| `packages/agents/AGENTS.md`, "Two runs", "How a step runs", "Cost and trace", "Routing" | `run_day`, the model wrapper, the stream of `AgentStep`, the injected handler, `chat.py:answer`; the paragraph saying the code has no `cost` and no `attempts` is deleted |
| `packages/agents/AGENTS.md`, "The state of an alert" | `queries` written from readings; `cost` and `attempts` as implemented |
| `packages/agents/skills/vigia/contrato.md` | the input names `tramo` |
| `apps/api/AGENTS.md` | the day run is consumed result by result, each answered with the transitions recorded; the `AgentStep`s are streamed from the run's stream |
| `evals/AGENTS.md` | the order of a day and the three alerts with one cause move to the cases the package runs without `apps/api`; new `ORQ-` cases: an earlier alert of equal severity covers a detection, a higher one does not; a refused transition ends its alert and the day goes on; a token cap reached mid-alert sends every later model step to its fallback; a run with no trace handler completes |
| `docs/superpowers/2026-10-03-tree-expansion-pending-3.md` | its status names this spec as run before it |
| `docs/guide/chapters/alert-journey.md` | the day-run and decision steps of its diagrams draw the generator and the verdict, each captioned `Draws:` with the section of `packages/agents/AGENTS.md` it draws |

## Acceptance

- `uv run pytest` in `packages/agents` holds a test per decision of this spec. Among them:
  - one planted violation per rule the validator gains on `severidad` and `tramos`;
  - the order of a day of three alerts with tied `pesos_en_riesgo`;
  - the coverage by earlier alerts at equal and at higher severity;
  - a refused transition;
  - an accepted `unida` that removes a later alert from the run;
  - one retry, then the fallback;
  - a token cap reached mid-alert;
  - a chat answer and a failed one;
  - the steps of an alert in their order;
  - a run with no trace handler.
- A detection on a stub reading carries every field of "The state of an alert", each figure with
  the `queryId` of its reading.
- The same day run twice proposes the same alert ids.
- No function of `packages/agents` takes a callable from `apps/api` that it calls to report back:
  `grep -rn "Callable" packages/agents/centinela_agents` names only the leaves, the reader, the
  classifier and the model.
- After the pages above change, the table in "Why" has no row left: every claim of
  `packages/agents/AGENTS.md` about the orchestrator's runtime is held by code, or the page says it
  is not.
