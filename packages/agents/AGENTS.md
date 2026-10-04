# packages/agents: the orchestrator and the five agents

This level holds the reasoning: the orchestrator and `Vigía`, `Analista`, `Estratega`, `Ejecutor`
and `Chat`. What runs: the validator of the decision tree, the walk of `detectar`, the catalogue and
reader the kernel hands the tree, the compiler of the tree to a LangGraph graph that pauses for a
person's decision, the compiler of the chat's subtree to a graph that never pauses, and the model
leaves `centinela_agents/orchestrator.py:CentinelaOrchestrator`
hands that compiler. Each leaf reads the kernel's `kpi_consultar` in code, loads its skill as the
model's instructions, and calls the provider
`centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)` returns,
behind a meter of its retry, cost and token cap. The day run,
`centinela_agents/day.py:run_day(graph, ctx, day, earlier, watched, limit, cause_rejections, proposal_rejections, tracer)`,
is a generator `apps/api` drives in its own process. `uv run pytest` holds the tree and the graph
with stub leaves, and the leaves with a mocked provider and kernel; `uv run pytest -m modelo` runs
the five agents against OpenAI and the kernel. What is decided, not built: log events beyond
`same_cause_dropped`, a policy search in the chat, and self-expansion. Each section that states one
opens with the marker. How the tree is written is [`arbol/AGENTS.md`](./arbol/AGENTS.md); how an agent's
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
| `centinela_agents/catalog.py` | the catalogue of KPI columns, the reader of a KPI on a day, and the connection to the kernel that builds both |
| `centinela_agents/evidence.py` | what a leaf reads of the kernel: each query under its `queryId`, each figure as a numbered fact, and the refusal of a figure no query returned |
| `centinela_agents/cache.py` | the in-process cache of model answers every provider of the factory sits behind |
| `centinela_agents/skills.py` | the loading of a skill as a model's instructions, and the rows of `skills/estratega/acciones.md` |
| `centinela_agents/predicate.py` | one comparison, and a threshold's value on a row |
| `centinela_agents/validator.py` | every refusal of a tree, and the loading of the base |
| `centinela_agents/state.py` | the state of an alert, the state of a chat question, and the fields a node may read |
| `centinela_agents/walk.py` | the walk of `detectar`, and the check that a detection still breaks |
| `centinela_agents/severity.py` | the severity and the `tramo` of a KPI row, and the refusals of a `severidad` or `tramos` block |
| `centinela_agents/day.py` | the alert id, the coverage by earlier alerts, the order of a day and the day run |
| `centinela_agents/metered.py` | the retry, the cost and the token cap of a model call, and its masking |
| `centinela_agents/privacy.py` | the masking scope a run opens and what it registers from a state ([masking every prompt](#masking-every-prompt)) |
| `centinela_agents/tracing.py` | the tracer the host injects |
| `centinela_agents/graph.py` | the compilers of the alert graph and of the chat graph, the interrupt, the resume, the fallbacks |
| `centinela_agents/failures.py` | the exceptions that name a leaf's failure |
| `centinela_agents/llm_provider.py`, `centinela_agents/ollama_provider.py`, `centinela_agents/openai_provider.py`, `centinela_agents/provider_factory.py` | the provider interface, its two implementations, and the choice between them by environment ([`PHASE_1_SETUP.md`](./PHASE_1_SETUP.md)) |
| `centinela_agents/schema.py` | also the output models of the leaves: `Cause`, `Action`, `ExecutedAction`, `Decision` ([`PHASE_2_SETUP.md`](./PHASE_2_SETUP.md)) |
| `centinela_agents/tools.py`, `centinela_agents/sql_vistas.py`, `centinela_agents/buscar_politica.py`, `centinela_agents/calcular_impacto.py`, `centinela_agents/action_tools.py` | the tool interfaces, their registry, the action stubs `Ejecutor` drafts with, and stubs of three tools no leaf calls ([`PHASE_3_SETUP.md`](./PHASE_3_SETUP.md)) |
| `centinela_agents/agents/` | the model leaves: `centinela_agents/agents/vigia.py`, `centinela_agents/agents/analista.py`, `centinela_agents/agents/estratega.py`, `centinela_agents/agents/ejecutor.py`, `centinela_agents/agents/chat.py`, and `centinela_agents/agents/orquestador.py`, the rejection classifier ([`PHASE_4_SETUP.md`](./PHASE_4_SETUP.md)) |
| `centinela_agents/orchestrator.py` | the leaves and the classifier wired into `Compiler`, with `start`, `run_day`, `resume`, `ask` and `use_thresholds`, which swaps the thresholds the compiled graph reads and keeps the paused alerts ([`PHASE_5_SETUP.md`](./PHASE_5_SETUP.md)) |
| `centinela_agents/security.py` | masking, secret detection, the screen of a prompt injection and a prompt builder by trust level; `Ejecutor` masks an email's prompt with it, and `Chat` screens and wraps a question with it ([`PHASE_6_SETUP.md`](./PHASE_6_SETUP.md)) |
| `centinela_agents/observability.py` | token, cost and latency counters per alert and agent, and a tracer that only logs; no running path uses it ([`PHASE_7_SETUP.md`](./PHASE_7_SETUP.md)) |
| `centinela_agents/output_validator.py` | checks of a leaf's output that only the tests run ([`PHASE_9_SETUP.md`](./PHASE_9_SETUP.md)) |
| `skills/` | what each agent is told ([`skills/AGENTS.md`](./skills/AGENTS.md)) |
| `tests/` | the validator's planted violations, the walk of `detectar`, the `ORQ-` cases of [`../../evals/AGENTS.md`](../../evals/AGENTS.md) that need no `apps/api` and no model, and the unit tests of each module above, `tests/test_evals.py` among them ([`PHASE_8_SETUP.md`](./PHASE_8_SETUP.md)); `tests/test_modelo.py` runs the five agents against the model and the kernel |
| `PHASE_1_SETUP.md` … `PHASE_9_SETUP.md` | one page per subsystem above, the detail this page links |
| `pyproject.toml`, `uv.lock` | the package, with `packages/tools`, the kernel's client, among its dependencies; `uv.lock` is written by uv ([`../../GENERATED.md`](../../GENERATED.md)) |

## Commands

Run from this directory, with [uv](https://docs.astral.sh/uv/), because the Python of the
development machine has no `ensurepip` and uv builds the environment without it:

| Command | What it does |
|---|---|
| `uv sync` | installs the package and its dependencies into `.venv` |
| `uv run pytest` | validates the base tree, runs the routing cases on the compiled graph with stub leaves, and the unit tests of the leaves with a mocked provider and kernel; no model is called, because `pyproject.toml` deselects the marker `modelo` |
| `uv run pytest -m modelo` | runs each agent's leaf against the model and the kernel the root `.env` and `.env.local` name, on the dataset's last day, in seconds on OpenAI; it skips when the provider has no key or does not answer, or the database does not |

## Decisions

- **LangGraph is the orchestrator**, because it keeps state per alert and pauses the graph for a
  person. The pause is the interrupt at the gate `aprobar.decision`, which every path to `Ejecutor`
  passes.
- **`Vigía` detects with rules, not with a model.** Its triggers are the thresholds of
  `data/metricas.yaml`, or the numbers its caller swaps in, applied by the nodes of `detectar`. z-score and trend are descriptive
  evidence and never trigger, because no document states a threshold for them.
- **The kernel reaches the tree through three inputs**: the catalogue of KPI columns the validator
  checks each `lee` against, `centinela_agents/catalog.py:catalog_from_kernel(answer)` over the
  answer of `kpi_catalogo`; the reader the interpreter calls with a metric and a simulated day,
  `centinela_agents/catalog.py:kernel_reader(call)` over `kpi_consultar`; and the call itself, which
  the leaves read through. `centinela_agents/catalog.py:connect_kernel(env)` builds all three from
  the DSNs of the environment. The reader and the leaves raise on a refusal, so a refused reading
  never passes for a day with no alert. The tree holds no connection of its own: the kernel's
  roles only read, as [`../../data/AGENTS.md`](../../data/AGENTS.md#rules-of-this-level) grants.

## Models

**Every agent runs on OpenAI's API, `gpt-4o-mini`, and the product stays able to run local
models.** A leaf calls a model through `centinela_agents/llm_provider.py:LLMProvider`, with
`generate_text(request)` for free text and `generate_structured(request)` for an output its JSON
schema fixes. `centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)`
chooses the implementation from `LLM_PROVIDER`, `openai` in the versioned `.env`, `ollama` when
unset, `anthropic` raising, and the model from `LLM_MODEL`, which has no default. Both are read when
`apps/api` first builds the orchestrator; the variables and the files they come from are
[`../../SETUP_OPENAI.md`](../../SETUP_OPENAI.md). Each leaf is a function of its provider, so a
test hands it a mock, and a machine that runs Ollama switches by the `.env` alone.

**Why the cloud: the team's hardware could not run a local model at the pace of a demo.** The
development machine, eight CPU cores, 9 GB of RAM and no GPU, ran `qwen3:4b-instruct` through
Ollama at about two and a half tokens a second: one alert took three to four minutes and the
integration test some ten, against a presentation of five. On `gpt-4o-mini` the agents' tests
take seconds. So the integration that runs and is tested end to end is the cloud one; the
local path, `centinela_agents/ollama_provider.py:OllamaProvider`, is built and unit-tested, and
was exercised against `qwen3:4b-instruct` until the time it took ruled it out, never as the
product's path.

- **`OpenAIProvider` passes the output's schema as a `json_schema` response format**, non-strict,
  because the leaves' schemas leave fields optional, and `OllamaProvider` passes it in Ollama's
  `format`: a model fills a schema more reliably than it writes free text, and a schema with no
  field for an action is an agent that cannot propose one.
- **The two tiers the brief asks for are a fast model and a reasoning slot**: every step uses
  `LLM_MODEL`, and `LLM_MODEL_RAZONA`, empty by default, names another model for `Analista` and
  `Estratega`, `centinela_agents/provider_factory.py:get_reasoning_provider()`. It is empty because
  the team's API key serves `gpt-4o-mini` alone. Each leaf still sends its `thinking` flag, which
  `OllamaProvider` passes as `think` and `OpenAIProvider` ignores, because a chat model of OpenAI
  takes no such parameter.
- **The code reads the kernel, and the model chooses and words.** A leaf reads its figures through
  `kpi_consultar` before the model runs, and hands them as numbered facts; the model cites a fact by
  its ref and writes `{0}` where it goes. `centinela_agents/evidence.py:Ledger` refuses a ref no
  query returned, `centinela_agents/evidence.py:stray_digits(text, allowed)` a figure written
  outside a placeholder, and `centinela_agents/evidence.py:fills(text, figures)` a placeholder with
  no figure, never renumbered, because a model copies a number wrong more often than it chooses a fact
  wrong, and one call per leaf is faster and cheaper than a loop of tool calls.
- **A repeated request pays once.** `centinela_agents/provider_factory.py:cached(provider)` puts
  every provider behind `centinela_agents/cache.py:CachingProvider(inner, size)`, an LRU of
  `CENTINELA_CACHE_RESPUESTAS` answers keyed by the model and everything the request sends, at
  temperature 0 only. A hit returns the stored answer with zero tokens and `cached` in its usage, so
  a day run again, a repeated eval or a reopened alert costs nothing, and a cost count never charges
  a hit. It lives in the process, because no agent writes anywhere. `OpenAIProvider` reports
  `cached_tokens` besides, the part of a prompt OpenAI served from its own prompt cache, which
  starts at 1,024 tokens of identical prefix: each prompt opens with its skill for that reason.
- **Every output is short and capped**: a title, one sentence of cause with at most two pieces of
  evidence, and one to three actions with an eight-word title, each call with its `max_tokens`,
  because each token is paid and waited for.

> **Limit.** Every prompt, with the alert's figures, reaches OpenAI's servers; its personal values
> leave as placeholders ([masking every prompt](#masking-every-prompt)). The key lives in the ignored
> `.env.local`, never in the versioned `.env`, because the repository is public and a key pushed to
> it is revoked.

### Masking every prompt

**Every model call is masked at the provider**, because it is the one place every prompt builder
passes, so no builder can forget a value. `centinela_agents/metered.py:MeteredProvider(inner)`
refuses a call made outside a masking scope with `centinela_agents/privacy.py:Unmasked`, replaces
in the system and the user prompt every value the scope's mapping holds
([`packages/tools`](../tools/AGENTS.md#masking)), records the masked prompt, and fills the
placeholders of the answer back before the leaf reads it, so every check of a leaf reads what it
read before masking. A placeholder the mapping lacks stays as written.

- **A run opens one mapping**: `centinela_agents/day.py:run_day(graph, ctx, day)` registers the
  entity of every earlier alert and every detection of the day, and hands the mapping to the graph
  through `centinela_agents/graph.py:run_config(alert_id, tracer, masking)`, whose `configurable`
  LangGraph never checkpoints for an object. A resume and a chat question open their own, and the
  rejection classifier its own in
  `centinela_agents/orchestrator.py:rejection_target(provider, state, catalog)`.
- **Each step teaches the mapping what it may write**: `leaf_node` registers the state through
  `centinela_agents/privacy.py:register_state(masking, catalog, state)`, and
  `centinela_agents/evidence.py:Ledger.consult(kpi, day)` every row it reads.
- **A typed id is resolved before the model reads it**: when the question holds a token with a
  digit, `centinela_agents/agents/chat.py:typed_entities(question, sources, day)` reads the rows
  of each KPI keyed by a personal column, so `clasificar` sends the id's placeholder and gets the id
  back. A placeholder no row holds is spelled by no question, so it selects no row.
- **The prompts travel in the state**, as `prompts`, and
  `centinela_agents/orchestrator.py:CentinelaOrchestrator.resume(alert_id, decision)` returns the
  ones its resume added as `resumed_prompts`, which `apps/api` logs.

**A local model, on a machine that can run one**, is admitted only when `ollama show <model>` lists
`tools` among its capabilities, from the Qwen3 family, one loaded at a time, because Ollama pays a
load on every switch. The tag `qwen3:4b` is the Thinking 2507 variant, which reasons whatever
`think` says, so a CPU takes the instruct variant.

| Machine | `LLM_PROVIDER` | `LLM_MODEL` | `LLM_MODEL_RAZONA` |
|---|---|---|---|
| the team's, and any without a GPU | `openai` | `gpt-4o-mini` | empty |
| 16 GB of RAM or more | `ollama` | `qwen3:8b` | empty |
| a GPU with 24 GB or more | `ollama` | `qwen3:14b` or `qwen3:30b-a3b` | a thinking model, when both fit |

## The universe

**An agent knows `data/csv/` and `data/policies/`, reached through the kernel's KPIs and the `v_*`
views, and nothing else.** No agent states a policy, a threshold or a fact those files do not hold;
when a question falls outside them, the answer says so. What the data cannot answer, and the answer
each topic gets, is the table of
[`skills/analista/politicas.md`](./skills/analista/politicas.md#what-the-policies-do-not-cover).

## What a leaf may use

**A leaf reads the kernel in code and gives its model no tool.**
`centinela_agents/evidence.py:Sources` hands each leaf the kernel's call, the catalogue, the metrics
and the tree's nodes. `Vigía` reads its KPI's row; `Analista` reads it and the rows every other KPI
holds for the same entity on the simulated day; `Estratega` reads the KPI's row for its parameters
and its impact. `Chat` reads the KPI the question names, or the anchored alert's.
`Ejecutor` receives the action tools of the registry `apps/api` builds.

> **Limit.** No leaf reads a `v_*` view or a policy: `centinela_agents/sql_vistas.py` and
> `centinela_agents/buscar_politica.py` are stubs no leaf calls, and `centinela_agents/tools.py`
> re-declares tools [`packages/tools`](../tools/AGENTS.md) owns. Its cost is a cause drawn from the
> kernel's KPIs alone, and the hypotheses of `skills/analista/<metric>.md`, which name views, go
> untested.

**Each agent answers one question, and no agent answers another's.** Which agent acts next is a
branch of the tree; what an agent may use once a leaf calls it is this section, because a tool is a
permission, not a route. What each receives and returns is its skill's contract.

| Agent | Its question | Model mode | Contract |
|---|---|---|---|
| `Vigía` | which written rule is broken on the simulated day, by which entity, and how many pesos it exposes? | none to detect; thinking off for the title | [`skills/vigia/contrato.md`](./skills/vigia/contrato.md) |
| `Analista` | why does it happen, according to the data and the policies? | thinking on | [`skills/analista/contrato.md`](./skills/analista/contrato.md) |
| `Estratega` | which action the policy prescribes fits, and what is it worth? | thinking on | [`skills/estratega/contrato.md`](./skills/estratega/contrato.md) |
| `Ejecutor` | how does the approved action become a draft, unchanged? | thinking off | [`skills/ejecutor/contrato.md`](./skills/ejecutor/contrato.md) |
| `Chat` | what do the data, an alert or the tree say about a person's question? | thinking off | [`skills/chat/contrato.md`](./skills/chat/contrato.md) |
| orchestrator | which step is the alert in, and who goes next? | thinking off, to classify a rejection reason | [`skills/orquestador/contrato.md`](./skills/orquestador/contrato.md) |

The tools are the ones [`packages/tools`](../tools/AGENTS.md) decides; this section gives each
agent its share.

### `Vigía` detects

- **Leaves:** `detectar`, which is code, `centinela_agents/walk.py:detect(ctx, day)`, and `titular`.
- **Tools:** `kpi_consultar`, in code, through the reader. No policy search: its thresholds are in
  `data/metricas.yaml`.
- **Ceiling:** it fires only where the walk of `detectar` reaches a leaf. Pesos at risk are the
  KPI's `pesos_en_riesgo` column, computed in SQL. One alert per metric and entity, whatever state
  the earlier one is in, because a rejected or executed alert whose rule still breaks would
  otherwise return every simulated day; it raises again only when its severity is higher than the
  highest earlier alert's, `centinela_agents/day.py:covered(detection, earlier)`.
- **Severity and `tramo`** are the metric's `severidad` and `tramos` blocks of `data/metricas.yaml`
  applied to the KPI row, `centinela_agents/severity.py:severity_of(metric, row, metrics)`. The
  detection reads its KPI through `centinela_agents/evidence.py:Ledger`, so its `cifra` and
  `pesos_en_riesgo` carry the reading's `queryId`, and its title cites them as figures.
- **Never:** explains, proposes, reads a policy.

### `Analista` explains

- **Leaves:** `explicar`.
- **Tools:** none for its model. Its leaf reads `kpi_consultar` for the alert's KPI and for every
  KPI that shares a column of the alert's entity, at most three rows each, and numbers each figure.
  *Decided, not built:* `sql_vistas` and `buscar_politica`.
- **Ceiling:** a cause holds when the facts show **the same entity**, **time** (the cause changes
  before or with the symptom) and **direction** (the cause moves the metric the way it moved). It
  draws no statistical inference, forecasts nothing and claims no more than "coincides with". At
  most one main cause and two contributing ones; hypotheses come from its skill for the alert's
  metric, plus one free hypothesis held to the same tests.
- **Same cause:** its prompt quotes, as data, each other alert in `nueva`, `en análisis` or
  `propuesta` with its metric, entity and cause's sentence, its placeholders filled in code, and
  its model may name one as `same_cause_as`, by the rule of its contract.
  `centinela_agents/agents/analista.py:same_cause(answer, cause, found, alert_id, metric)` keeps
  the id only when it is one of those alerts, not this one, of another metric, and the cause is
  `identified`, and logs the drop otherwise. Another alert of the same metric is another entity,
  because an alert is one per metric and entity, and two entities with one kind of cause are two
  causes. The nodes of `explicar` then merge.
- **Never:** looks for new alerts, proposes an action, estimates an impact, answers a question.

### `Chat` answers a question

**The chat is an agent of its own, on its own root of the tree, `conversar.raiz`**, because it is
the first agent that reads a person's free text, and its controls must hold in code and in the
validator, not in a prompt shared with `Analista`. Each question stands alone: there is no history,
and the only context is the alert it is anchored to.

- **Leaves:** `clasificar` and `responder`, which
  `centinela_agents/orchestrator.py:CentinelaOrchestrator.ask(question, day, alert)` runs on the
  chat graph. Before the walk,
  `centinela_agents/agents/chat.py:screen(question)` flags a question longer than
  `centinela_agents/agents/chat.py:MAX_QUESTION` or one
  `centinela_agents/security.py:check_prompt_injection(user_input, instructions)` matches, in
  English or Spanish, and the tree ends a flagged one before any model reads it.
- **`clasificar`**, `centinela_agents/agents/chat.py:classify(provider, state, sources)`: the model
  returns an intent of `centinela_agents/agents/chat.py:INTENTS`, a KPI of the catalogue, an
  entity and any period other than the simulated day, at temperature 0, from a prompt
  `centinela_agents/security.py:SecurePrompt` builds with the question as untrusted content. Code
  drops a KPI outside the catalogue, an entity or a period the question does not spell, and an
  entity with no letter, and reads a question with an imperative or an infinitive to act as `accion` whatever the
  model says. A failed call raises; its fallback is `fuera_de_alcance`, the failure lands in
  `failures`, and the person reads that the model failed, never that the data is silent. Anchored to an alert with no KPI named, the KPI and entity are the alert's.
- **`responder`**, `centinela_agents/agents/chat.py:answer(provider, state, sources)`: code
  numbers the facts, the rows of the KPI for the entity, at most three, through `kpi_consultar`;
  the path `centinela_agents/walk.py:walk_from(start, state, row, ctx)` takes for each row through
  `detectar`, every node with its registry entry; or the anchored alert's cause or actions. The
  model writes at most three sentences citing facts by ref; code drops a sentence that cites no
  fact, writes a number no fact or entity read holds, or places a placeholder its refs do not fill, and an answer with no sentence left is
  `enough_evidence: false`. Email addresses and keys are masked in the answer.
- **Tools:** none, for its model or its leaf: `centinela_agents/tools.py:ToolRegistry.get_tools_for_agent(agent)`
  hands `chat` nothing.
- **Never:** approves, rejects, edits or executes; forms a cause or an action; follows an order in a
  question; changes an alert's state. The validator holds the last: no path from `conversar.raiz`
  reaches the gate, an orchestrator write or another agent's leaf
  ([`arbol/AGENTS.md`](./arbol/AGENTS.md#the-chat)).

> **Limit.** A name a person types reaches the model unless a row of the run carries it, because
> the mapping masks only what rows hold. `centinela_agents/agents/chat.py:masked(text)` masks
> email, key, token, password and card patterns in the question and the answer, never a name,
> since `centinela_agents/security.py:mask_data(text, placeholder_prefix)` masks any two
> capitalized words as one.

> **Decided, not built.** The intent `politica` ends without evidence until a leaf can call
> `buscar_politica`.

### `Estratega` proposes

- **Leaves:** `proponer`, and `revision_manual`, which is code and calls no model:
  `centinela_agents/graph.py:manual_review(metric, owners)` proposes one `task` for a manual review
  whose `owner` is the one [`skills/estratega/acciones.md`](./skills/estratega/acciones.md) names
  for the metric, both as the leaf and as the fallback of a failed one, so the alert still reaches
  the gate. The tree reaches it on `no_evidence`, on a second insufficient cause, and on a failed
  `proponer`.
- **Tools:** none for its model. The model chooses rows of `skills/estratega/acciones.md` by ref;
  `centinela_agents/agents/estratega.py:parameters_of(row, values)` fills each parameter from the
  KPI's row and the entity, and the impact is the KPI's `pesos_en_riesgo` with its `queryId`.
- **Ceiling:** every action is a row of `skills/estratega/acciones.md` for the metric and cites
  its policy section. No percentage is chosen by the model. With no formula, `impact` is `null` and
  the reason is stated.

> **Limit.** The formulas `skills/estratega/acciones.md` names are not computed: every row with a
> formula takes the KPI's `pesos_en_riesgo` as its impact, and `price_increase_pct` and `units`,
> which only a formula yields, stay out of `parameters`. Its cost is a price or purchase draft a
> person completes by hand.
- **Never:** reopens the cause, which it returns as an insufficient cause; executes.

### `Ejecutor` acts after a decision

- **Leaves:** `ejecutar`, for an action whose type has a tool in `packages/tools`, and
  `nota_manual`, for one that has none. Either receives the alert id, the approved action with an
  edit's `parameters`, and the recorded decision, and nothing else of the state,
  `centinela_agents/graph.py:leaf_node(node, function, ctx, token_cap)`; the alert id travels for
  the idempotency [`packages/tools`](../tools/AGENTS.md#actions-and-idempotency) decides.
- **Tools:** none for its model. The leaf calls the action tool in code, a draft or a sandbox
  effect; the model writes the body of an approved `email_draft` and the text of a manual note.
- **Ceiling: no discretion.** It passes the approved `parameters` unchanged. The stubs of
  `centinela_agents/action_tools.py` name each draft by its inputs,
  `centinela_agents/action_tools.py:stable_id(prefix, parts)`, so a second run names the same
  draft. The prompt of an email draft passes `centinela_agents/security.py:mask_data(text, placeholder_prefix)`, then the provider's mapping, which masks the recipient's id.
- **Result:** a Spanish sentence code composes from the parameters, plus an email's body.
- **Never:** chooses between actions, recomputes, adds a recipient, runs without a recorded decision.

## The orchestrator

It is the only part that knows which step an alert is in. It walks the tree and keeps nothing else
to decide: every route is a branch of the tree, and the interpreter decides only how a step runs.
It is code, except the step that classifies a rejection reason.

- **Input:** to run a day, `run_day` with the simulated day, the earlier alerts as
  `centinela_agents/day.py:Earlier`, the watched metrics, the cap and the rejection reasons by
  metric. To start one alert,
  `centinela_agents/graph.py:stream_alert(graph, detection, alert_id, day, earlier_alerts, alert_briefs, cause_rejections, proposal_rejections, tracer)`,
  which `start_alert` runs to its end: the detection, the alert id, the simulated day, the earlier
  alerts with their briefs, and the metric's rejection reasons, already split by the agent that
  reads them. To resume one,
  `centinela_agents/graph.py:resume(graph, alert_id, decision, tracer)` with the decision `apps/api`
  recorded. The version of the tree comes through `centinela_agents/graph.py:Compiler`. A start on
  an alert whose thread has ended runs on a fresh thread, `centinela_agents/graph.py:fresh(graph, alert_id)`,
  so nothing of the earlier run stays, and a start on one that awaits a decision is refused.
- **Tools: none.** No step needs a query, a policy or an action, so the graph gives it no tool.
- **Output:** `run_day` yields a `centinela_agents/day.py:Step` per step, then per alert a
  `centinela_agents/day.py:AlertRun`, the graph's state (the transitions it proposes, the log
  events, the target of a rejection reason) with the later detections it absorbed, or a
  `centinela_agents/day.py:AlertFailed` when the graph raised, which takes no verdict, and the day
  goes on. The caller answers each `AlertRun` with a `centinela_agents/day.py:Verdict`:
  `recorded` false ends that alert, because the record wins over the checkpoint; `refused_merge`
  names a target the caller would not join, with no absorption, and the alert runs again on a
  fresh thread without it; `absorbed` names the later detections the caller stored `unida`, which
  the run drops.
- **Ceiling:** it moves an alert only along a branch of the tree and passes each agent's output on
  unchanged. The only text a person reads that it writes is the fallback of a failed step.
- **Never:** detects, explains, proposes, executes, computes a figure, opens a database connection,
  persists the lifecycle, or resumes an alert past the interrupt without a recorded decision.

> **Limit.** The decision the graph expects carries `id`, `kind`, `simulated_day`, `actionId`,
> `parameters` and `reason`, and the states it proposes are Spanish (`nueva`, `en análisis`,
> `propuesta`, `aprobada`, `rechazada`, `unida`, `ejecutada`). The web's
> `apps/web/src/api/types.ts:Decision` carries no `id` and no day,
> `apps/web/src/api/types.ts:AlertStatus` is English. `apps/api` translates between them, and
> nothing decides how.

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
state; *Read by* is what each is meant to use of it. A key a leaf returns that the state does not
declare is dropped without a trace, so the leaves return none.

| Field | Written by | Read by |
|---|---|---|
| `alert_id`, `simulated_day`, `entry` (the leaf `detectar` reached) | `start_alert` | every node, `apps/api` |
| `detection`: `metric`, `entity`, `path` (each node of `detectar` and its branch), `row` (the KPI row), `cifra`, `regla`, `fuente_umbral`, `severity`, `tramo`, `pesos_en_riesgo` | `start_alert`, from the detection | the leaves, `ejecutar.vigente` through `still_breaks` |
| `earlier_alerts`: the state of each earlier alert, by id | `start_alert` | `estado.same_cause_as.status`, `Analista` |
| `alert_briefs`: the metric, entity and cause of each earlier alert, by id | `start_alert` | `Analista` |
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
| `queries`: the detection's reading, then each `kpi_consultar` a leaf ran, with its `queryId`, KPI, day and SQL | `start_alert`, then the leaves of `Vigía`, `Analista` and `Estratega` | the fallback of `explicar`, for `queriesReviewed`; `apps/api`, which logs each as `evidence` |
| `cost`: by agent, the prompt tokens, completion tokens, calls and cached answers | each leaf node | `apps/api`, which persists it |
| `prompts`: each masked prompt, its agent, system and user text | each leaf node and the rejection's end | `apps/api`, which logs each as `prompt` |

### How a step runs

**A fallback writes a value, never a route**, `centinela_agents/graph.py:fallback(leaf, state,
error, ctx)`: the metric's `descripcion` and the entity for the title, `no_evidence` for the cause,
no actions for the proposal, the manual review's task for `revision_manual`, and no executed action
for `Ejecutor`. The tree routes each at `explicar.con_evidencia`, `proponer.con_acciones` and
`ejecutar.resultado`. The failure lands in `failures` with its step and kind,
`centinela_agents/graph.py:failure_kind(error)` over the exceptions of
`centinela_agents/failures.py`, and the `reason` of a failed `explicar` is the Spanish sentence
`centinela_agents/graph.py:REASONS` holds for that kind, worded for a manager; the error itself is logged as a warning.

**A resume is refused** for each case of `centinela_agents/graph.py:decision_problem(decision,
state)`, and when nothing awaits a decision; `ejecutar.vigente` reads the KPI on the day the
decision names. The graph never passes the gate on a decision `apps/api` did not record.

**The loop to `Analista` is capped at one return**, because each pass is a paid model run, and a cause that fails `Estratega` twice is one the data does not support with a
listed action, which is the case manual review exists for. A `request_changes` is capped at one per
alert by [`apps/api`](../../apps/api/AGENTS.md#decisions-and-roles), which states why. **A decision never expires**: no policy states a deadline, so the interrupt waits.

**A step fails when its model call fails twice.** The orchestrator wraps each provider in
`centinela_agents/metered.py:MeteredProvider(inner)`, and `leaf_node` opens
`centinela_agents/metered.py:metering(agent, spent, cap)` around each leaf, so a call is retried
once on a timeout, a connection error or an answer that is not valid JSON; an output its
schema refuses goes straight to the fallback, which
[`DOUBTS.md`](../../DOUBTS.md) files as a debt. The OpenAI client is built with no retries of its
own, so the meter's one retry is the only one. The timeout is the
provider's `ModelConfig.timeout_seconds`, because its HTTP client is the only place that can stop a
call. The cap is `centinela_agents/orchestrator.py:TOKEN_CAP` tokens per alert, checked before
each call and counted over the whole alert, so once it is reached every model step left takes its
fallback, an approved `Ejecutor` step after the gate included. A cached answer
charges nothing, and a failure carries its `attempts`. The rejection classifier runs in an end
node, not a leaf, so its call is neither retried nor counted in `cost`.

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

### The chat graph

**A question walks its own graph**, `centinela_agents/graph.py:compile_chat(tree, *, leaves, metrics, catalog, reader, token_cap)`,
compiled from `conversar.raiz` with the same predicate, leaf and end nodes as the alert graph, no
checkpointer and no interrupt, because a question never waits for a person.
`centinela_agents/state.py:ChatState` holds the question, the day, the anchored alert with its
`cause` and `actions`, the chat's own fields under `chat`, the `answer`, the `queries` and the
`costs`. `ask` takes the anchored alert's cause, actions and entity from the alert's own thread
when this process holds it, and from what `apps/api` hands otherwise, and returns the end, the
steps the walk took, the `centinela_agents/schema.py:ChatAnswer`
`centinela_agents/agents/chat.py:closing(state, metrics)` writes for that end, the queries, the screen's
result, the failures and the costs. A chat run touches no alert's state, proposes no transition and
does not wait for the day run.

### The day run

**The day run is `run_day`, a generator, because the dependency rule of
[the root page](../../AGENTS.md#how-the-parts-connect) lets `apps/api` call `packages/agents` and
forbids the reverse**: it yields each result and waits for the caller's verdict. It walks
`detectar` for every row of every KPI on the simulated day, `centinela_agents/walk.py:detect(ctx, day)`,
keeps the watched metrics, drops what `covered` covers, orders the rest with
`centinela_agents/day.py:ordered(detections, day, limit)`, and runs the alert graph of each **in
series**. An alert's merge candidates are only the earlier alerts in `propuesta`, the one state
whose graph waits, and the day's detections not yet run; one the caller records in `propuesta`
joins them. Its id is `centinela_agents/day.py:alert_id(metric, entity, day)`, a hash, because
entity values hold spaces and accents and the id travels in URLs and thread ids, so a day run
twice proposes the same ids.

**The order is the largest `pesos_en_riesgo` of each metric, then the rest by pesos, then severity,
then id, and a day raises at most the cap its caller passes**, `CENTINELA_ALERTAS_POR_DIA` in
`apps/api`, three by default. A null pesos sorts last, because an unmeasured exposure cannot claim
the inbox first; severity and id order a tie the same way on every run. In series, because a local
model is loaded once and parallel requests share its memory and compute, and in the cloud the order of the inbox is the
order of the run. A metric first, because a metric with hundreds of rows would otherwise fill every
day. By pesos, because the largest exposure reaches the
inbox first, and because a merge keeps the alert analysed first, which is the larger:
`explicar.destino_analizado` joins this alert to one analysed before it, and
`explicar.destino_nuevo` joins to this alert one the day run has not reached. Capped, because the
dataset's last day breaks a threshold in some two hundred and fifty rows and an alert costs seconds
of model; the rest fire again on a later day, when the earlier ones are in the inbox.

### Cost, trace and log

**The chat's leaves report their cost**: each returns the step, the model, the prompt and
completion tokens and the latency in `costs`, `centinela_agents/agents/chat.py:costed(provider, request, step)`,
and `apps/api` logs it.

**Each leaf writes its start and its end to the graph's stream**, with
`centinela_agents/graph.py:STEP_LABELS` and whether it failed, and `run_day` passes them on as
`Step`s, opening each alert with its detection's step: a stream, not a callback, for the dependency
rule. The orchestrator's own steps write none, because `apps/web/src/api/types.ts:Agent` names the
agents alone.

**Tracing is a handler the host injects**, `centinela_agents/tracing.py:langfuse_tracer(env)`:
Langfuse's LangChain handler, which is why `langchain` is a dependency beside `langfuse`, when
`LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, and none otherwise, because a trace
observes and never decides. A trace groups by session: the alert id for an alert's start and
resume, its own for a chat question. The trace shows the graph's nodes and not the model
generations, because the leaves call the provider SDKs directly, not through LangChain. The detection runs no graph, so it has no trace.

> **Decided, not built.** The only event the graph writes is `same_cause_dropped`, in
> `centinela_agents/graph.py:effects(node_id, branch, state)`.

- **Each output reaches `apps/api` as a log event** of `apps/web/src/api/types.ts:LogEventType`: a
  detection and a merge as `alert`, a `Cause` as `evidence`, the actions as `proposal`, an executed
  draft as `action` then `result`. The target of a rejection reason joins the `decision` event
  `apps/api` writes for the person.

### What is not the orchestrator's

`apps/api` consumes the day run and answers each result with the verdict of what it recorded,
checks that a decision's role may make it and that an edit keeps the action's keys, calls the
resume, keeps the rejection reasons, validates and persists each transition the orchestrator
proposes, stores the checkpoint, persists cost, streams the steps and owns the `bitácora`: its
page is [`apps/api`](../../apps/api/AGENTS.md). Idempotency of an action is decided to be
`packages/tools`'; `centinela_agents/action_tools.py` holds it in this package instead.

## Coverage: every metric has one owner per step

| Step | Owner | Reads, per metric |
|---|---|---|
| detect | `Vigía` | its L3 branch of `detectar`, and its `umbrales` in `data/metricas.yaml` |
| explain | `Analista` | the KPIs that share its entity; `skills/analista/<metric>.md` names hypotheses no leaf tests yet |
| propose | `Estratega` | the metric's rows in `skills/estratega/acciones.md` |
| execute | `Ejecutor` | the approved action alone |

**A gap is a refusal**: the validator refuses a metric missing any of the first three, so the base
does not load with a gap ([`arbol/AGENTS.md`](./arbol/AGENTS.md#the-validator)). **The gaps between
agents, closed:** a person's question belongs to `Chat`; pesos at risk belong to `Vigía` and what an action
recovers to `Estratega`; two alerts with one cause are marked by `Analista` and merged by the
orchestrator; a policy passage that gives orders is reported, never obeyed, by `Analista` and
`Estratega`; personal data is masked by the mapping of `packages/tools` before any model reads it.

## Rules of this level

- **A route is a branch of the tree.** No code outside the interpreter decides which step an alert
  takes, so a change of route is a change to `arbol/base.yaml`. *The validator refuses an invalid
  base at startup, and `uv run pytest` holds the routes.*
- **The model never produces a number.** Every figure in a title, an explanation or a proposal
  comes from a `kpi_consultar` the leaf ran, and its `queryId` travels with the figure as evidence.
  *`centinela_agents/evidence.py` refuses a cited fact no query returned and a figure written
  outside a placeholder, and `tests/test_agents.py` and `tests/test_modelo.py` hold it.*
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
