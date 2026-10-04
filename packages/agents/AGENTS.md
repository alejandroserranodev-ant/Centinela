# packages/agents: the orchestrator and the four agents

This level holds the reasoning: the orchestrator and `Vigía`, `Analista`, `Estratega` and
`Ejecutor`. What runs: the validator of the decision tree, the walk of `detectar`, the catalogue and
reader the kernel hands the tree, the compiler of the tree to a LangGraph graph that pauses for a
person's decision, and the model leaves `centinela_agents/orchestrator.py:CentinelaOrchestrator`
hands that compiler, each calling the provider
`centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)` returns.
`apps/api` builds that orchestrator in its own process. `uv run pytest` holds the tree and the
graph with stub leaves, and the leaves with a mocked provider. What is decided, not built: the
leaves' use of real tools and of their skills, the retry and the token cap, the day run, its
de-duplication and its order, cost in the state, Langfuse traces, `AgentStep` emission, log events
beyond `same_cause_dropped`, the chat route and self-expansion. Each section that states one opens
with the marker. How the tree is written is [`arbol/AGENTS.md`](./arbol/AGENTS.md); how an agent's
instructions are written is [`skills/AGENTS.md`](./skills/AGENTS.md); what the challenge asks of
each agent is [`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md); how a provider
is configured is [`../../SETUP_OPENAI.md`](../../SETUP_OPENAI.md).

## Why each file exists

| Path | Why it exists |
|---|---|
| `arbol/` | the base of the decision tree and its registry ([`arbol/AGENTS.md`](./arbol/AGENTS.md)) |
| `centinela_agents/schema.py` | the tree's schema and its closed lists |
| `centinela_agents/yaml_loader.py` | a YAML loader that reads only `true` and `false` as booleans |
| `centinela_agents/metrics.py` | the descriptions and `umbrales` of `data/metricas.yaml`, and a threshold's shapes |
| `centinela_agents/catalog.py` | the catalogue of KPI columns and the reader of a KPI on a day, from the kernel |
| `centinela_agents/predicate.py` | one comparison, and a threshold's value on a row |
| `centinela_agents/validator.py` | every refusal of a tree, and the loading of the base |
| `centinela_agents/state.py` | the state of an alert and the fields a node may read |
| `centinela_agents/walk.py` | the walk of `detectar`, and the check that a detection still breaks |
| `centinela_agents/graph.py` | the compiler to the LangGraph graph, the interrupt, the resume, the fallbacks |
| `centinela_agents/failures.py` | the exceptions that name a leaf's failure |
| `centinela_agents/llm_provider.py`, `centinela_agents/ollama_provider.py`, `centinela_agents/openai_provider.py`, `centinela_agents/provider_factory.py` | the provider interface, its two implementations, and the choice between them by environment ([`PHASE_1_SETUP.md`](./PHASE_1_SETUP.md)) |
| `centinela_agents/schema.py` | also the output models of the leaves: `Cause`, `Action`, `ExecutedAction`, `Decision` ([`PHASE_2_SETUP.md`](./PHASE_2_SETUP.md)) |
| `centinela_agents/tools.py`, `centinela_agents/sql_vistas.py`, `centinela_agents/buscar_politica.py`, `centinela_agents/calcular_impacto.py`, `centinela_agents/action_tools.py` | the tool interfaces a leaf receives, their registry, and stubs that return empty or zero results ([`PHASE_3_SETUP.md`](./PHASE_3_SETUP.md)) |
| `centinela_agents/agents/` | the model leaves: `centinela_agents/agents/vigia.py`, `centinela_agents/agents/analista.py`, `centinela_agents/agents/estratega.py`, `centinela_agents/agents/ejecutor.py`, and `centinela_agents/agents/orquestador.py`, the rejection classifier ([`PHASE_4_SETUP.md`](./PHASE_4_SETUP.md)) |
| `centinela_agents/orchestrator.py` | the leaves and the classifier wired into `Compiler`, with `start` and `resume` ([`PHASE_5_SETUP.md`](./PHASE_5_SETUP.md)) |
| `centinela_agents/security.py` | masking, secret detection and a prompt builder by trust level, which no leaf calls ([`PHASE_6_SETUP.md`](./PHASE_6_SETUP.md)) |
| `centinela_agents/observability.py` | token, cost and latency counters per alert and agent, and a tracer that only logs ([`PHASE_7_SETUP.md`](./PHASE_7_SETUP.md)) |
| `centinela_agents/output_validator.py`, `centinela_agents/orchestrator_v2.py` | checks of a leaf's output, and an orchestrator that adds them and the counters ([`PHASE_9_SETUP.md`](./PHASE_9_SETUP.md)) |
| `skills/` | what each agent is told ([`skills/AGENTS.md`](./skills/AGENTS.md)) |
| `tests/` | the validator's planted violations, the walk of `detectar`, the `ORQ-` cases of [`../../evals/AGENTS.md`](../../evals/AGENTS.md) that need no `apps/api` and no model, and the unit tests of each module above, `tests/test_evals.py` among them ([`PHASE_8_SETUP.md`](./PHASE_8_SETUP.md)) |
| `PHASE_1_SETUP.md` … `PHASE_9_SETUP.md` | one page per subsystem above, the detail this page links |
| `pyproject.toml`, `uv.lock` | the package, with `packages/tools` for the tests, which validate the base against the catalogue the kernel serves; `uv.lock` is written by uv ([`../../GENERATED.md`](../../GENERATED.md)) |

## Commands

Run from this directory, with [uv](https://docs.astral.sh/uv/), because the Python of the
development machine has no `ensurepip` and uv builds the environment without it:

| Command | What it does |
|---|---|
| `uv sync` | installs the package and its dependencies into `.venv` |
| `uv run pytest` | validates the base tree, runs the routing cases on the compiled graph with stub leaves, and the unit tests of the leaves with a mocked provider; no model is called |

> **Limit.** `centinela_agents/openai_provider.py` imports `openai`, which `pyproject.toml` does not declare, so
> `uv run pytest` stops collecting at `tests/test_providers.py`, and `centinela_agents/provider_factory.py`, which
> imports it, fails in an environment built by `uv sync` alone. With the package supplied,
> `uv run --with openai --with requests pytest` collects every test, and some unit tests of the
> leaves, the providers, `centinela_agents/security.py`, `centinela_agents/output_validator.py` and the tool stubs fail; that command
> lists them.

## Decisions

- **LangGraph is the orchestrator**, because it keeps state per alert and pauses the graph for a
  person. The pause is the interrupt at the gate `aprobar.decision`, which every path to `Ejecutor`
  passes.
- **`Vigía` detects with rules, not with a model.** Its triggers are the thresholds of
  `data/metricas.yaml`, applied by the nodes of `detectar`. z-score and trend are descriptive
  evidence and never trigger, because no document states a threshold for them.
- **The kernel reaches the tree through two inputs**: the catalogue of KPI columns the validator
  checks each `lee` against, `centinela_agents/catalog.py:catalog_from_kernel(answer)` over the
  answer of `kpi_catalogo`, and the reader the interpreter calls with a metric and a simulated day,
  `centinela_agents/catalog.py:kernel_reader(call)` over `kpi_consultar`. The reader raises on a
  refusal, so a refused reading never passes for a day with no alert. The tree never opens a
  connection, because no agent does.

## Models

**A leaf calls a model through `centinela_agents/llm_provider.py:LLMProvider`**, with
`generate_text(request)` for free text and `generate_structured(request)` for an output its JSON
schema fixes. `centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)`
chooses the implementation from `LLM_PROVIDER` (`ollama` by default, or `openai`; `anthropic`
raises) and the model from `LLM_MODEL`, which has no default. Both are read when `apps/api` first
builds the orchestrator; the variables and the files they come from are
[`../../SETUP_OPENAI.md`](../../SETUP_OPENAI.md). Each leaf is a function of its provider, so a
test hands it a mock.

- **`OllamaProvider` passes the output's schema in Ollama's `format` parameter**, because a small
  model fills a schema more reliably than it writes free text, and a schema with no field for an
  action is an agent that cannot propose one. `OpenAIProvider` asks only for a JSON object and
  validates nothing against the schema.
- **The two tiers the brief asks for are one model in two modes**: thinking on where an agent
  reasons (`Analista`, `Estratega`), thinking off where a step classifies, routes or words a finding
  (`Vigía`'s title, `Ejecutor`, the classifier).

> **Limit.** `OpenAIProvider` sends the prompt, and the data in it, to OpenAI's servers, against
> the decision below that no data leaves the machine; nothing refuses `LLM_PROVIDER=openai`. Its
> cost is every alert's figures and entity names leaving the machine, unmasked, because no leaf
> calls `centinela_agents/security.py`. `OllamaProvider` sends `thinking` where Ollama reads `think`, so thinking on
> never reaches the model.

> **Decided, not built.** The model the team runs.

- **Every model runs locally through Ollama**, because the team requires that no data leaves the
  machine and the brief accepts open models through Ollama. One family, Qwen3, and one model loaded
  at a time, because Ollama pays a load on every switch and the development machine has no room for
  two. A model is admitted only when `ollama show <model>` lists `tools` among its capabilities.

  | Machine | Model |
  |---|---|
  | CPU only, under 16 GB of RAM | `qwen3:4b` |
  | 16 GB or more | `qwen3:8b`, the team's default |
  | a GPU with 24 GB or more | `qwen3:14b` or `qwen3:30b-a3b` |

## The universe

**An agent knows `data/csv/` and `data/policies/`, reached through the kernel's KPIs and the `v_*`
views, and nothing else.** No agent states a policy, a threshold or a fact those files do not hold;
when a question falls outside them, the answer says so. What the data cannot answer, and the answer
each topic gets, is the table of
[`skills/analista/politicas.md`](./skills/analista/politicas.md#what-the-policies-do-not-cover).

## What a leaf may use

> **Decided, not built**, except what names its code. Each leaf of `centinela_agents/agents/`
> calls its model with a prompt written inline, loads no skill, and calls none of the tools it
> receives. `centinela_agents/tools.py:ToolRegistry.get_tools_for_agent(agent)` hands each agent
> the share the table below gives it, and `apps/api` builds the registry empty.

> **Limit.** `centinela_agents/tools.py` and its stubs re-declare in this package the tools
> [`packages/tools`](../tools/AGENTS.md) owns, and nothing here imports `centinela_tools`. Its cost
> is two definitions of each tool, and a leaf wired to the stub instead of the kernel's
> `kpi_consultar`: its figures come from no query.

**Each agent answers one question, and no agent answers another's.** Which agent acts next is a
branch of the tree; what an agent may use once a leaf calls it is this section, because a tool is a
permission, not a route. What each receives and returns is its skill's contract.

| Agent | Its question | Model mode | Contract |
|---|---|---|---|
| `Vigía` | which written rule is broken on the simulated day, by which entity, and how many pesos it exposes? | none to detect; thinking off for the title | [`skills/vigia/contrato.md`](./skills/vigia/contrato.md) |
| `Analista` | why does it happen, according to the data and the policies? | thinking on | [`skills/analista/contrato.md`](./skills/analista/contrato.md) |
| `Estratega` | which action the policy prescribes fits, and what is it worth? | thinking on | [`skills/estratega/contrato.md`](./skills/estratega/contrato.md) |
| `Ejecutor` | how does the approved action become a draft, unchanged? | thinking off | [`skills/ejecutor/contrato.md`](./skills/ejecutor/contrato.md) |
| orchestrator | which step is the alert in, and who goes next? | thinking off, to classify a rejection reason | [`skills/orquestador/contrato.md`](./skills/orquestador/contrato.md) |

The tools are the ones [`packages/tools`](../tools/AGENTS.md) decides; this section gives each
agent its share.

### `Vigía` detects

- **Leaves:** `detectar`, which is code, `centinela_agents/walk.py:detect(ctx, day)`, and `titular`.
- **Tools:** `kpi_consultar`, in code, through the reader. No policy search: its thresholds are in
  `data/metricas.yaml`.
- **Ceiling:** it fires only where the walk of `detectar` reaches a leaf. Pesos at risk are the
  KPI's `pesos_en_riesgo` column, computed in SQL. One alert per metric and entity, whatever state
  the earlier one is in; it raises again only when severity rises a tier above the highest earlier
  alert, because a rejected or executed alert whose rule still breaks would otherwise return every
  simulated day.
- **Never:** explains, proposes, reads a policy.

> **Limit.** Severity has no definition anywhere in the tree: `apps/web/src/api/types.ts:Severity`
> types it, and no metric, KPI or rule computes it, while raising again and [the order](#the-day-run)
> rest on it. The earlier alerts that
> `centinela_agents/graph.py:start_alert(graph, detection, *, alert_id, day, earlier_alerts, cause_rejections, proposal_rejections)`
> receives are `{id: status}` only, so no step can compare a metric, an entity or a severity with
> them.

### `Analista` explains, and answers the chat

- **Leaves:** `explicar`, and `responder_chat` on the chat's own route.
- **Tools:** `sql_vistas`, read-only SQL over the views, and `buscar_politica`, policy search.
- **Ceiling:** a cause holds when queries show **the same entity**, **time** (the cause changes
  before or with the symptom) and **direction** (the cause moves the metric the way it moved). It
  draws no statistical inference, forecasts nothing and claims no more than "coincides with". At
  most one main cause and two contributing ones; hypotheses come from its skill for the alert's
  metric, plus one free hypothesis held to the same tests. In the chat it answers with figures from
  queries, and asked what to do, it quotes `Estratega`'s proposal for the anchored alert or says
  there is none.
- **Never:** looks for new alerts, proposes an action, estimates an impact.

### `Estratega` proposes

- **Leaves:** `proponer`, and `revision_manual`, which is code and calls no model: the host
  supplies its function (`centinela_agents/orchestrator.py` supplies `proponer`'s model leaf instead, so a manual
  review calls the model), which proposes one `task` for a manual review whose `owner` is the one
  [`skills/estratega/acciones.md`](./skills/estratega/acciones.md) names for the metric. When that
  function fails, `centinela_agents/graph.py:manual_review(metric, ctx)` proposes the same task, so
  the alert still reaches the gate. The tree reaches it on `no_evidence`, on a second insufficient
  cause, and on a failed `proponer`.
- **Tools:** `sql_vistas`, `buscar_politica`, and `calcular_impacto`.
- **Ceiling:** every action is a row of `skills/estratega/acciones.md` for the metric and cites
  its policy section. No percentage is chosen by the model: the calculator computes it. With no
  formula, `impact` is `null` and the reason is stated.
- **Never:** reopens the cause, which it returns as an insufficient cause; executes.

### `Ejecutor` acts after a decision

- **Leaves:** `ejecutar`, for an action whose type has a tool in `packages/tools`, and
  `nota_manual`, for one that has none. Either receives the alert id, the approved action with an
  edit's `parameters`, and the recorded decision, and nothing else of the state,
  `centinela_agents/graph.py:leaf_node(node, function, ctx)`.
- **Tools:** none for its model. The leaf calls the action tool in code, a draft or a sandbox
  effect; the model writes the body of an approved `email_draft` and the text of a manual note.
- **Ceiling: no discretion.** It passes the approved `parameters` unchanged, keyed by alert and
  action so a second run has no effect. *Decided, not built:* the stubs of
  `centinela_agents/action_tools.py` name each draft with a random id, so a second run makes a
  second draft.
- **Never:** chooses between actions, recomputes, adds a recipient, runs without a recorded decision.

## The orchestrator

It is the only part that knows which step an alert is in. It walks the tree and keeps nothing else
to decide: every route is a branch of the tree, and the interpreter decides only how a step runs.
It is code, except the step that classifies a rejection reason.

- **Input:** to start an alert, `start_alert` above: the detection, the alert id, the simulated
  day, the earlier alerts, and the rejection reasons `apps/api` kept for the metric, already split
  by the agent that reads them. To resume one,
  `centinela_agents/graph.py:resume(graph, alert_id, decision)` with the decision `apps/api`
  recorded. The version of the tree comes through `centinela_agents/graph.py:Compiler`.
- **Tools: none.** No step needs a query, a policy or an action, so the graph gives it no tool.
- **Output:** the state of each alert's graph: the transitions it proposes, the log events, the
  target of a rejection reason.
- **Ceiling:** it moves an alert only along a branch of the tree and passes each agent's output on
  unchanged. The only text a person reads that it writes is the fallback of a failed step.
- **Never:** detects, explains, proposes, executes, computes a figure, opens a database connection,
  persists the lifecycle, or resumes an alert past the interrupt without a recorded decision.

> **Limit.** The decision the graph expects carries `id`, `kind`, `simulated_day`, `actionId`,
> `parameters` and `reason`, and the states it proposes are Spanish (`nueva`, `en análisis`,
> `propuesta`, `aprobada`, `rechazada`, `unida`, `ejecutada`). The web's
> `apps/web/src/api/types.ts:Decision` carries no `id` and no day,
> `apps/web/src/api/types.ts:AlertStatus` is English, and
> `apps/web/src/api/types.ts:ChatQuestion` has no route in the graph. `apps/api` translates
> between them, and nothing decides how.

### The alert graph

**One thread per alert, the alert id as the thread id.** The host injects the checkpointer, because
an agent never opens a database connection; where the checkpoint is stored is `apps/api`'s. The
checkpoint is working state, never the lifecycle record. Each run compiles the version it is handed,
cached by `Compiler` per version and a hash of its content. The graph holds a node for each leaf,
each predicate node and each end reachable from a `vigia` leaf `detectar.raiz` reaches.

**A predicate node is a graph node, not only the function of an edge.** It evaluates its predicate,
records its id and branch in `camino`, applies the write bound to that branch, and its edge reads
the target it chose. So the path an alert walked is in its state, a branch carries the
orchestrator's own write, and the gate `aprobar.decision` is where the graph pauses on LangGraph's
`interrupt()` until `resume` hands it the recorded decision.

### The state of an alert

`centinela_agents/state.py:AlertState` declares it. Every leaf but `Ejecutor`'s receives the whole
state; *Read by* is what each is meant to use of it.

> **Limit.** `centinela_agents/agents/vigia.py:redact_title(provider, detection)` and
> `centinela_agents/agents/analista.py:explain_cause(provider, alert, tools)` read `metric`, `entity` and `cifra` at the top of the state, where it
> holds them under `detection`, so each prompts its model with no metric and no entity. Every
> leaf also returns an `error` key the state does not declare.

| Field | Written by | Read by |
|---|---|---|
| `alert_id`, `simulated_day`, `entry` (the leaf `detectar` reached) | `start_alert` | every node, `apps/api` |
| `detection`: `metric`, `entity`, `path` (each node of `detectar` and its branch), `row` (the KPI row) | `start_alert` | the leaves, `ejecutar.vigente` through `still_breaks` |
| `earlier_alerts`: the state of each earlier alert, by id | `start_alert` | `estado.same_cause_as.status` |
| `cause_rejections`, `proposal_rejections` | `start_alert`; a `request_changes` adds to the second | `Analista`, `Estratega` |
| `title` | `Vigía` | `apps/api` |
| `cause`, `same_cause_as` | `Analista`, or the fallback | `Estratega`, the nodes of `explicar`, `apps/api` |
| `actions`, `insufficient_cause` | `Estratega`, or `revision_manual` | the nodes of `proponer`, `apps/api`; `Ejecutor` receives the approved one |
| `decision` | the gate, from `resume` | the nodes of `aprobar`, `Ejecutor` |
| `executed_action` | `Ejecutor` | `ejecutar.resultado`, `apps/api` |
| `analyst_returns`, `proposal_returns` | the bound writes | the capped returns |
| `merged_into`, `merged_alerts`, `rejection_target`, `fin` | the ends and the bound writes | `apps/api` |
| `status`: the state the graph last proposed or the decision set | the orchestrator | the orchestrator |
| `transitions`: each `[alert id, state]` the graph proposes | the orchestrator | `apps/api` |
| `camino`, `next_node`, `failures`, `events` | the orchestrator | `apps/api`; `next_node` the edges |
| `queries` | no code; the fallback of `explicar` reads it for `queriesReviewed` | `apps/api` |

### How a step runs

**A fallback writes a value, never a route**, `centinela_agents/graph.py:fallback(leaf, state,
error, ctx)`: the metric's `descripcion` and the entity for the title, `no_evidence` for the cause,
no actions for the proposal, the manual review's task for `revision_manual`, and no executed action
for `Ejecutor`. The tree routes each at `explicar.con_evidencia`, `proponer.con_acciones` and
`ejecutar.resultado`. The failure lands in `failures` with its step and kind,
`centinela_agents/graph.py:failure_kind(error)` over the exceptions of
`centinela_agents/failures.py`, and the `reason` of a failed `explicar` is the Spanish sentence
`centinela_agents/graph.py:REASONS` holds for that kind.

**A resume is refused** for each case of `centinela_agents/graph.py:decision_problem(decision,
state)`, and when nothing awaits a decision; `ejecutar.vigente` reads the KPI on the day the
decision names. The graph never passes the gate on a decision `apps/api` did not record.

**The loop to `Analista` is capped at one return**, because each pass is a thinking run on the one
loaded model, and a cause that fails `Estratega` twice is one the data does not support with a
listed action, which is the case manual review exists for. A `request_changes` is capped at one per
alert by [`apps/api`](../../apps/api/AGENTS.md#decisions-and-roles), which states why. **A decision never expires**: no policy states a deadline, so the interrupt waits.

> **Decided, not built.** A step fails when its model call fails twice: the call is retried once on
> a timeout, a connection error or an output its schema refuses. A step also fails when the alert
> reaches its token cap, checked after each call, and every model step left on that alert then
> takes its fallback. The timeout per call and the token cap are settings of the graph, sized to the
> machine that runs Ollama. A failure is to carry its `attempts`. A transition `apps/api` refuses
> ends that alert's run, because the record wins over the checkpoint.

### Routing

**A rejection reason goes to the classifier** at `fin.rechazada`, the only step of the orchestrator
that calls a model, with [`skills/orquestador/contrato.md`](./skills/orquestador/contrato.md). The
host hands it to `compile_tree` as `classify`; its target is one of
`centinela_agents/graph.py:REJECTION_TARGETS`, and decides who reads the reason on the next run of
the same metric: `causa` to `Analista`, `propuesta` to `Estratega`, `ambos` to both, and `ninguno`
to no agent, the reason staying in the `bitácora`. `centinela_agents/orchestrator.py:rejection_target(provider, state)`
is that `classify`: it hands
`centinela_agents/agents/orquestador.py:classify_rejection(provider, reason, cause, actions)` the
decision's reason, the cause and the actions, and returns its `destino`;
`centinela_agents/graph.py:classified(classify, state)` answers `ninguno` when it fails. `apps/api` keeps the reason with its target, metric and entity,
and hands it in split into `cause_rejections` and `proposal_rejections`, so each agent learns only
from its own mistakes.

> **Decided, not built.** **The chat always goes to `Analista`, in chat mode, with no
> classifier**, because the chat belongs to `Analista`. The anchored alert comes from `apps/api`
> with the question, so `Analista` can quote its `actions`. A chat run touches no alert's state and
> proposes no transition. A chat question does not wait for the day run, only for the model call in
> course.

### The day run

> **Decided, not built.** Only its walk exists, `centinela_agents/walk.py:detect(ctx, day)`.

**The day run is code and keeps no checkpoint.** Advancing the clock hands it the simulated day: it
walks `detectar` for every row of every KPI, drops each detection an earlier alert covers, orders
the rest, and runs the alert graph of each **in series**. It names an alert by metric, entity and
simulated day, so a day run twice proposes the same ids and `apps/api` refuses the second.

**The order is by `pesos_en_riesgo` from the largest**, ties broken by severity from `critical`
down, then by alert id. In series, because one model is loaded and parallel requests share its
memory and compute. By pesos, because the largest exposure reaches the inbox first, and because a
merge keeps the alert analysed first, which is the larger: `explicar.destino_analizado` joins this
alert to one analysed before it, and `explicar.destino_nuevo` joins to this alert one the day run
has not reached.

### Cost, trace and log

> **Decided, not built.** The state has no `cost`, no trace is opened, no `AgentStep` is emitted,
> and the only event the graph writes is `same_cause_dropped`, in
> `centinela_agents/graph.py:effects(node_id, branch, state)`.
> `centinela_agents/observability.py:MetricsCollector` counts tokens, cost and latency per agent,
> and `centinela_agents/observability.py:LangfuseTracer` logs instead of tracing; only
> `centinela_agents/orchestrator_v2.py` uses them, and nothing imports `centinela_agents/orchestrator_v2.py`.

- **After each model call the orchestrator adds Ollama's `prompt_eval_count`, `eval_count` and one
  call to the alert's `cost`, under the agent that made it.** A chat answer carries its own cost.
  `apps/api` persists both.
- **Each alert is one Langfuse trace, its id the alert id**, opened when the day run hands the
  detection to the alert graph; the resume adds its spans to the same trace. The detection of a day
  is a trace of its own, and so is each chat question.
- **An `AgentStep` marks when an agent's leaf starts and ends**, with a Spanish `description`, never
  for the orchestrator's own steps, because `apps/web/src/api/types.ts:Agent` names the four agents.
- **Each output reaches `apps/api` as a log event** of `apps/web/src/api/types.ts:LogEventType`: a
  detection and a merge as `alert`, a `Cause` as `evidence`, the actions as `proposal`, an executed
  draft as `action` then `result`. The target of a rejection reason joins the `decision` event
  `apps/api` writes for the person.

### What is not the orchestrator's

`apps/api` checks that a decision's role may make it and that an edit keeps the action's keys,
calls the resume, keeps the rejection reasons, validates and persists each transition the
orchestrator proposes, stores the checkpoint, persists cost, streams `AgentStep` and owns the
`bitácora`: its page is [`apps/api`](../../apps/api/AGENTS.md). Idempotency of an action and
masking personal data are `packages/tools`'; `centinela_agents/security.py` masks in this package
instead, and no leaf calls it.

## Coverage: every metric has one owner per step

| Step | Owner | Reads, per metric |
|---|---|---|
| detect | `Vigía` | its L3 branch of `detectar`, and its `umbrales` in `data/metricas.yaml` |
| explain | `Analista` | `skills/analista/<metric>.md`: its hypotheses and the views that test them |
| propose | `Estratega` | the metric's rows in `skills/estratega/acciones.md` |
| execute | `Ejecutor` | the approved action alone |

**A gap is a refusal**: the validator refuses a metric missing any of the first three, so the base
does not load with a gap ([`arbol/AGENTS.md`](./arbol/AGENTS.md#the-validator)). **The gaps between
agents, closed:** the chat belongs to `Analista`; pesos at risk belong to `Vigía` and what an action
recovers to `Estratega`; two alerts with one cause are marked by `Analista` and merged by the
orchestrator; a policy passage that gives orders is reported, never obeyed, by `Analista` and
`Estratega`; personal data is masked in `packages/tools` before any agent sees it.

## Rules of this level

- **A route is a branch of the tree.** No code outside the interpreter decides which step an alert
  takes, so a change of route is a change to `arbol/base.yaml`. *The validator refuses an invalid
  base at startup, and `uv run pytest` holds the routes.*
- **The model never produces a number.** Every figure in an explanation or a proposal comes from a
  tool call, and the call travels with the figure as evidence. *No gate holds this*, and the leaves
  break it: the schemas of `centinela_agents/agents/analista.py` and `centinela_agents/agents/estratega.py` ask the model for each figure's
  `value` and `queryId` and for each action's `impact`, and no tool call backs them.
- **An agent is given only the tools its section of "What a leaf may use" names.** No model is
  given an action tool: the leaf `ejecutar` calls it in code. *No gate holds this.*
- **One cause, one alert**, ranked by pesos at risk. *`uv run pytest` holds the merge.*
- **"Not enough evidence" is a complete answer.** An agent that cannot support a claim says so
  instead of guessing, and states its confidence and assumptions when it can. *No gate holds this.*
- **A rejection's reason is kept** and read back by the agent its target names. *No gate holds this.*
- **Every agent runs at autonomy level `Propone`**: it proposes, and a person decides. *The
  validator holds it: no path reaches `Ejecutor` without passing `aprobar.decision`.*
- **A change to a skill, a prompt or the tree runs `uv run pytest`** and the set in
  [`../../evals/AGENTS.md`](../../evals/AGENTS.md).
