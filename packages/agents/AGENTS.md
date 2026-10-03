# packages/agents: the orchestrator and the four agents

This level holds the reasoning: the orchestrator and `Vigía`, `Analista`, `Estratega` and
`Ejecutor`. It holds the decision tree, its validator and its interpreter as code; the agents hold
no code yet, and this page states the domain each is built against. What the challenge asks of each
agent is [`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its agents section. How
an agent's instructions are written is [`skills/AGENTS.md`](./skills/AGENTS.md).

## Why each file exists

| Path | Why it exists |
|---|---|
| `arbol/base.yaml` | the base of the decision tree: the laws, and every node, leaf and end the orchestrator walks |
| `arbol/fundamentos.yaml` | the registry: every clause and policy section a node may rest on |
| `centinela_agents/` | the schema of the tree, its validator, the walk of `detectar`, and the compiler to the LangGraph graph |
| `skills/` | what each agent is told ([`skills/AGENTS.md`](./skills/AGENTS.md)) |
| `tests/` | one planted violation per rule of the validator, the walk of `detectar`, and the `ORQ-` cases of [`../../evals/AGENTS.md`](../../evals/AGENTS.md) that need no `apps/api` |
| `pyproject.toml`, `uv.lock` | the package and its pinned dependencies; `uv.lock` is written by uv ([`../../GENERATED.md`](../../GENERATED.md)) |

## Commands

Run from this directory, with [uv](https://docs.astral.sh/uv/), because the Python of the
development machine has no `ensurepip` and uv builds the environment without it:

| Command | What it does |
|---|---|
| `uv sync` | installs the package and its dependencies into `.venv` |
| `uv run pytest` | validates the base tree and runs the routing cases on the compiled graph, with stub leaves and no model |

## Decisions

- **LangGraph is the orchestrator**, because it keeps state per alert and pauses the graph for human
  approval. The approval is the interrupt at the gate `aprobar.decision`, which every path to
  `Ejecutor` passes.
- **Every model runs locally through Ollama**, because the team requires that no data leaves the
  machine and the brief accepts open models through Ollama. One family, Qwen3, and one model loaded
  at a time, because Ollama pays a load on every switch and the development machine has no room for
  two. The model is sized to the machine that runs Ollama:

  | Machine | Model |
  |---|---|
  | CPU only, under 16 GB of RAM | `qwen3:4b` |
  | 16 GB or more | `qwen3:8b`, the team's default |
  | a GPU with 24 GB or more | `qwen3:14b` or `qwen3:30b-a3b` |

  A model is admitted only when `ollama show <model>` lists `tools` among its capabilities.
- **The two tiers the brief asks for are one model in two modes**: thinking on (`think: true`)
  where an agent reasons (`Analista`, `Estratega`), thinking off where a step classifies, routes or
  words a finding. Which mode a step uses is decided per step, not per agent.
- **Every model call passes the JSON schema of its output in Ollama's `format` parameter**, because
  a small model fills a schema more reliably than it writes free text, and a schema with no field
  for an action is an agent that cannot propose one.
- **`Vigía` detects with rules, not with a model.** Its triggers are the thresholds in
  `metricas.yaml` (see [`../../data/AGENTS.md`](../../data/AGENTS.md)). z-score and trend are
  computed and shown as descriptive evidence and never trigger, because no document states a
  threshold for them.
- **The kernel reaches the tree through two inputs**: the catalogue of KPI columns the validator
  checks each `lee` against, and a reader the interpreter calls with a metric and a simulated day.
  The tree never opens a connection, because no agent does.

## The universe

**An agent knows `data/csv/` and `data/policies/`, reached through the `v_*` views, and nothing
else.** No agent states a policy, a threshold or a fact those files do not hold. When a question
falls outside them, the answer says so.

**What the data cannot answer, and no agent covers:**

| Topic | Why it is outside |
|---|---|
| payment agreements "registered in the system" (`FIN-POL-004` §6) | no table records them |
| the quarterly review of a credit limit (`FIN-POL-004` §3) | no history of `cupo_credito` |
| strategic customers with a shorter term (`FIN-POL-004` §2) | no column marks them |
| written approval to sell below cost (`COM-POL-002` §4) | no field records it; an agent says "no approval is recorded in the data", never "the policy was breached" |
| splitting orders to evade a cap (`COM-POL-002` §4) | the policy does not say how to recognise it, and defining it would invent a rule |
| public holidays in "10 business days" (`OPE-POL-007` §4) | no calendar; business days are Monday to Friday, stated as an assumption |
| an email address or phone of a customer or supplier | none exists; a draft addresses `cliente_id` or `proveedor_id` and `apps/web` resolves the name |
| the goals of a customer or of the company, such as a sales target over six months | no table records them |

## What a leaf may use

**Each agent answers one question, and no agent answers another's.** Which agent acts next is a
branch of the decision tree, in the next section; what an agent may use once a leaf calls it is
this one, because a tool is a permission, not a route.

| Agent | Its question | Model mode |
|---|---|---|
| `Vigía` | which written rule is broken today, by which entity, and how many pesos it exposes? | none to detect; thinking off to word the title |
| `Analista` | why does it happen, according to the data and the policies? | thinking on |
| `Estratega` | which action the policy prescribes fits, and what is it worth? | thinking on |
| `Ejecutor` | how does the approved action become a draft, unchanged? | thinking off, for the body of an email only |
| orchestrator | which step is the alert in, and who goes next? | thinking off, to classify a rejection reason only |

### `Vigía` detects

- **Input:** the simulated day, and the metric, entity and severity of every earlier alert.
- **Tools:** read-only SQL over the views `metricas.yaml` names, filtered by the simulated day.
  No policy search: its thresholds are already in `metricas.yaml`.
- **Leaves:** `detectar`, the walk of the stage `detectar` in code, and `titular`, the title.
- **Output:** a detected alert: metric, entity, simulated day, the triggering figure with its
  `queryId`, the broken rule with its `fuente_umbral`, severity, the `tramo` when the metric
  defines `tramos`, and pesos at risk with its `queryId`.
- **Ceiling:** it fires only where the walk of `detectar` reaches a leaf, which compares a KPI with
  its `umbrales` in `metricas.yaml` on the simulated day. Pesos at risk follow the metric's
  `pesos_en_riesgo`, computed in SQL. One alert per metric and entity, whatever state the earlier
  one is in; it raises again only when severity rises a tier above the highest earlier alert,
  because a rejected or executed alert whose rule still breaks would otherwise return every
  simulated day.
- **Never:** explains, proposes, reads a policy.

### `Analista` explains, and answers the chat

- **Input:** a detected alert, or a chat question.
- **Tools:** read-only SQL over every view, and policy search.
- **Leaves:** `explicar`, and `responder_chat` on the chat's own route.
- **Output:** a `Cause` as `apps/web/src/api/types.ts` declares it: `identified` with a sentence and
  its evidence, or `no_evidence` with the reason and the queries reviewed, plus a `Confidence`.
  It may add the id of another open alert the same cause explains.
- **Ceiling:** a cause holds when queries show three things: **the same entity** (the cause touches
  the alert's entity), **time** (the cause changes before or with the symptom), and **direction**
  (the cause moves the metric the way it moved). It draws no statistical inference, forecasts
  nothing and claims no more than "coincides with". At most one main cause and two contributing
  ones. Hypotheses come from its skill for the alert's metric, plus one free hypothesis held to the
  same three tests.
- **In the chat** it answers about the data and the alerts with figures from queries. Asked what to
  do, it quotes `Estratega`'s proposal for the alert, or says there is none.
- **Never:** looks for new alerts, proposes an action, estimates an impact.

### `Estratega` proposes

- **Input:** the alert, its `Cause`, and the rejection reasons kept for its metric, the reason of a
  `request_changes` among them.
- **Leaves:** `proponer`, and `revision_manual`, which is code and calls no model: one `task` for a
  manual review and nothing else, whose `owner` is the one `skills/estratega/acciones.md` names for
  the metric. The tree reaches it on `no_evidence`, on a second insufficient cause, and on a failed
  `proponer`.
- **Tools:** read-only SQL, policy search, and the impact calculator in `packages/tools`.
- **Output:** one to three `Action`s with `impact` and `confidence`.
- **Ceiling:** every action is a row of `skills/estratega/acciones.md` for the metric, and
  cites its policy section. No percentage is chosen by the model: a price change is the one that returns
  the line to `margen_minimo_pct` or passes the cost increase through, as the calculator computes
  it. With no formula, `impact` is `null` and the reason is stated.
- **Never:** reopens the cause (it returns the alert to the orchestrator as an insufficient cause),
  executes.

### `Ejecutor` acts after approval

- **Input:** the approved or edited action, with the decision `apps/api` recorded.
- **Leaves:** `ejecutar`, for an action whose type has a tool in `packages/tools`, and
  `nota_manual`, for one that has none: a `task` naming the manual step for a person. Either
  receives the approved action and the recorded decision, and nothing else of the alert's state.
- **Tools:** none for its model. The node `ejecutar` calls the action tool in code, each a draft or
  a sandbox effect, and the model is called only to write the body of an approved `email_draft`.
- **Output:** an `ExecutedAction`.
- **Ceiling: no discretion.** It passes the approved `parameters` unchanged, keyed by alert and
  action so a second run has no effect. The model writes only the body of an email, with the
  figures it is given and the tone `FIN-POL-004` §6 sets: courteous, written, copied to the seller.
- **Never:** chooses between actions, recomputes, adds a recipient, runs without a recorded decision.

### The orchestrator interprets the tree

It is the only part that knows which step an alert is in. It walks the decision tree and keeps
nothing else to decide: every route is a branch of the tree, and the interpreter decides only how a
step runs. It is code, except one step that classifies a rejection reason.

- **Input:** from `apps/api`, one of three: the simulated day with the metric, entity, severity and
  state of every earlier alert; a recorded decision (the `Decision`, its id, the role that made it
  and the simulated day it was made) to resume one alert; or a `ChatQuestion` with its anchored
  `Alert`, if any. With the first two, the rejection reasons `apps/api` keeps for the alert's
  metric. With each, the version of the tree to walk.
- **Tools: none.** Each step that might want one reads its input instead: the order reads
  `pesosAtRisk`, which `Vigía` computed in SQL; the check on `same_cause_as` reads the earlier
  alerts `apps/api` hands in; the classifier reads the reason, the `Cause` with its evidence, and
  the actions with their impact and parameters, each placeholder replaced by its figure. No step
  needs a query, a policy or an action, so the graph gives it no tool.
- **Output:** the state of each alert's graph; an `AgentStep` when an agent's node starts and when
  it ends, with a Spanish `description`, never for its own steps, because `Agent` names the four
  agents only; and, to `apps/api`, the transitions it proposes, the log events, the target of a
  rejection reason, and the cost of each alert.
- **Ceiling:** it moves an alert only along a branch of the tree, and passes each agent's output on
  unchanged. The only text a person reads that it writes is the fallback of a failed step, fixed in
  "How a step runs" below. It names an alert by metric, entity and simulated day, so a day run twice
  proposes the same ids and `apps/api` refuses the second.
- **Never:** detects, explains, proposes, executes, computes a figure, opens a database connection,
  persists the lifecycle, or resumes an alert past the interrupt without a recorded decision.

## The orchestrator's graph

### Two runs

**The day run is code and keeps no checkpoint.** Advancing the clock hands it the simulated day: it
walks the stage `detectar` for every row of every KPI, `centinela_agents/walk.py:detect(ctx, day)`,
checks each detection against the earlier alerts, orders the detected alerts, and runs the alert
graph of each one **in series**, in that order.

**The alert graph is LangGraph, compiled from the tree, one thread per alert, the alert id as the
thread id.** Its host injects the checkpointer, because an agent never opens a database connection;
where the checkpoint is stored is `apps/api`'s. The checkpoint is working state, never the
lifecycle record.

### The decision tree

**The tree is data, validated by code and walked by a deterministic interpreter; a model acts
only at a leaf.** Its base is [`arbol/base.yaml`](./arbol/base.yaml), beside the registry
[`arbol/fundamentos.yaml`](./arbol/fundamentos.yaml), because routing is the orchestrator's
concern. It is YAML, as `metricas.yaml` is, whose `umbrales` its predicates apply. A client's
version is not a file: `apps/api` keeps it and hands it to each run, because no agent writes
anywhere.

**Every entry of the registry that cites a standard names a numbered clause, confirmed against its
licensed text before a node rests on it.** The texts are licensed and are not in the repository, so
the person who adds an entry confirms its clause in the review of its pull request, and an entry
with no clause number is refused there, because no reader can check it.

**The tree compiles to the LangGraph graph; an invalid base stops the start.**
`centinela_agents/validator.py:load_base(arbol, metricas, skills, catalog)` validates the base and
raises with every problem. `centinela_agents/graph.py:compile_tree(tree, *, leaves, metrics,
catalog, reader, classify, checkpointer, owners)` makes a graph node of each leaf, each predicate node and
each end reachable from a `vigia` leaf that `detectar.raiz` reaches, and a conditional edge out of
each predicate node. Each run compiles the version `apps/api` hands in, cached by its `version` and
a hash of its content, by `centinela_agents/graph.py:Compiler`, because two clients may hold
different trees under one version number.

**A predicate node is a graph node, not only the function of an edge.** It evaluates its
predicate, records its id and branch in `camino`, applies the write bound to that branch, and its
edge reads the target it chose. So the path an alert walked is in its state, a branch can carry
the orchestrator's own write, and the gate `aprobar.decision` is where the graph pauses: it calls
LangGraph's `interrupt()`, and `centinela_agents/graph.py:resume(graph, alert_id, decision)`
resumes it with the recorded decision.

#### The node

```yaml
- id: detectar.cartera.saldo_vencido.dias
  fundamento: fin-pol-004.s4
  predicado: { lee: kpi.saldo_vencido.max_dias_vencido, op: ">", umbral: saldo_vencido }
  si: hoja.vigia.titular
  no: detectar.cartera.saldo_vencido.cupo
- id: hoja.vigia.titular
  hoja: { agente: vigia, decision: titular, skill: vigia/contrato.md }
  sigue: hoja.analista.explicar
```

| Field | Rule |
|---|---|
| `id` | unique; its first segment is a stage (`detectar`, `explicar`, `proponer`, `aprobar`, `ejecutar`, `cerrar`, `medir`), or `hoja` for a leaf |
| `fundamento` | the id of one entry of the registry; required on a node, absent on a leaf, which inherits its parent's |
| `predicado.lee` | a KPI column (`kpi.<metric>.<column>`), read only in `detectar`, or a field of the alert's state (`estado.<field>`) |
| `predicado.op` | one of `>`, `>=`, `<`, `<=`, `=`, `!=`, `en` (membership in a closed list written in the node), `existe`; quoted in YAML, except `en` and `existe` |
| `predicado.umbral` or `predicado.valor` | `umbral` names a metric of `metricas.yaml` or an approved KPI, and the value compared is its `umbrales` entry for the column `lee` reads; `valor` is a literal, admitted only for a state field |
| `si`, `no` | both required, each a node, a leaf or an end |
| `hoja` | `agente`, a `decision` from that agent's closed list, and `skill`, a file under `skills/` the step starts from |
| `sigue` | on a leaf only: where the walk continues once the agent returns |

| Agent | Its closed list of decisions |
|---|---|
| `vigia` | `detectar` (code), `titular`, `proponer_kpi`, `expandir` |
| `analista` | `explicar`, `responder_chat`, `expandir` |
| `estratega` | `proponer`, `revision_manual` (code), `expandir` |
| `ejecutor` | `ejecutar`, `nota_manual`, `expandir` |

**A predicate holds no literal threshold**, so a threshold stays in `metricas.yaml`; a threshold
whose text has two conditions is two nodes. A comparison with a null value is false, so a row a KPI
cannot measure fires nothing. A `lee` on the state names a field of "The state of an alert" below,
a field of the candidate the day run walks `detectar` with (`estado.candidato.metrica`,
`estado.candidato.descriptivo`), or a field the orchestrator derives when a node reads it:
`estado.same_cause_as.status`, the state of the named alert among the earlier alerts;
`estado.action.type`, the type of the approved action; and `estado.detection.vigente`, below.
`centinela_agents/state.py:STATE_FIELDS` is the list the validator checks.

#### The levels

| Level | Holds | Changed by |
|---|---|---|
| L0 | the laws, `leyes` in the base, each on one entry of the registry | a pull request only |
| L1 | every node whose id names no metric family: each stage's entry, its gates, its capped returns | a pull request only |
| L2 | one branch per metric family, `<stage>.<family>`: `cartera`, `margen`, `inventario`, `comercial`, `abastecimiento`, `clientes` | the stage's agent by self-expansion, or a pull request |
| L3 | the nodes of one metric and their leaves, `<stage>.<family>.<...>` | the stage's agent by self-expansion, or a pull request |

**L1 is every node that names no family, not one node per stage**, because the gates and the
capped returns are the same for every metric and must never move by self-expansion. A leaf's
stage is its agent's. `cerrar` has no node: it is the set of ends below, which `apps/api` closes.
`medir` has no node in the base, because its only decision, `proponer_kpi`, has no leaf in it.

#### The ends

| End | What the interpreter does on reaching it |
|---|---|
| `fin.sin_alerta` | ends the walk of `detectar`: no alert |
| `fin.unida` | writes `merged_into` and proposes `unida` |
| `fin.rechazada` | runs the classifier of the rejection reason; an exception or a target outside its closed list is `ninguno` |
| `fin.recarga_agotada` | ends a second `request_changes`, which `resume` refuses before it reaches the graph |
| `fin.ya_no_aplica` | records that the condition no longer holds; the alert stays `aprobada`, and `Ejecutor` is not called |
| `fin.ejecutada` | proposes `ejecutada` |
| `fin.fallo_ejecucion` | records the failure; the alert stays `aprobada` |

**The orchestrator's own writes are bound to L1 nodes by id**, in
`centinela_agents/graph.py:effects(node_id, branch, state)`, because L1 changes only by pull
request. `explicar.destino_nuevo` on `si` absorbs the named alert into this one and proposes
`unida` for it; on `no` it drops `same_cause_as` and logs it. `proponer.retorno_disponible` on `si`
counts a return to `Analista`. `aprobar.recarga_disponible` on `si` counts the `request_changes`,
keeps its reason in `proposal_rejections`, and clears the decision, so the gate waits again.
Entering an `analista` leaf from `nueva` proposes `en análisis`, and entering `aprobar.decision`
proposes `propuesta` once. A leaf that runs again clears the outputs of its decision it does not
return, `centinela_agents/graph.py:LEAF_OUTPUTS`, so a second proposal never keeps the first's
`insufficient_cause`.

#### The validator

`centinela_agents/validator.py:problems(data, grounds)` refuses a tree where:

- a node fails the schema, or a predicate fails the atomicity test: more than one operand, an
  `umbral` and a `valor` together, `en` without a closed list;
- a `valor` spells a boolean another way, `True`, `yes`, `on` or the like: the tree's YAML reads only
  `true` and `false` as booleans, so any other spelling would be text that never equals a boolean;
- a node lacks its `fundamento`, its `si` or its `no`, or rests on an id absent from the registry;
- a path from `detectar.raiz` reaches an `Ejecutor` leaf without passing `aprobar.decision` and
  `ejecutar.vigente`;
- the graph has a cycle other than the two capped returns, the `si` of
  `proponer.retorno_disponible` to `explicar` and of `aprobar.recarga_disponible` to `proponer`,
  each reading the counter `effects` counts equal to 0;
- a branch names no node, leaf or end of the closed list, a node reaches no end, or `detectar.raiz`
  does not reach a node or leaf, because an orphan `vigia` leaf would be an entry no walk checks;
- a `lee` names a KPI column the catalogue does not hold, a state field `STATE_FIELDS` does not
  declare, or a KPI outside `detectar`, because an alert reads its measure only through
  `ejecutar.vigente`;
- a KPI node of `detectar` is reached where the candidate may be another metric, because the walk
  would read one metric's column on another's row;
- an `umbral` names a metric absent from `metricas.yaml` and from the approved KPIs, or one with no
  threshold for the column `lee` reads;
- a leaf's `skill` is no file under `skills/`, or its `decision` is outside its agent's list;
- a metric of `metricas.yaml` has no L3 branch in `detectar`, no file in `skills/analista/`, or no
  row in `skills/estratega/acciones.md`;
- L0 or an L1 node differs from the base, or a leaf of the base changes its agent, its decision or
  its `sigue`; a new leaf is allowed, so a branch grows without rerouting the base.

The catalogue is an input: the validator checks each `lee` on a KPI against the catalogue it is
handed, never against a database. `uv run pytest` plants one violation per rule.

#### The node ejecutar.vigente

Before every `Ejecutor` leaf, `ejecutar.vigente` reads `estado.detection.vigente`:
`centinela_agents/walk.py:still_breaks(state, ctx)` reads, on the simulated day of the decision,
the KPI row of the alert's entity and re-applies each node of `detectar` the detection passed on
`si`, with the same `umbral`. `si` goes on to `ejecutar.automatizable`; `no`, no row for the
entity, or a path none of whose KPI nodes is left in the tree, ends at `fin.ya_no_aplica`, because
nothing runs on a condition no node can check again. Two rows for one entity raise, and the resume
fails, because the entity is the key of the KPI and a second row breaks the kernel's contract. It is
code, so `Ejecutor` keeps no discretion, and it rests on `iso9001.10.2.1.c`: an action addresses a
nonconformity, which a resolved one no longer has.

### How a step runs

The fallback of a failed step, the token cap, the retry and the order of a day's alerts are
settings of the interpreter, not nodes, because they decide how a step runs, not which step runs.

**A resume is refused** without a recorded decision id or the simulated day of the decision, with a
kind outside `approve`, `edit`, `reject` and `request_changes`, with a reject or a `request_changes`
that carries no reason, with an approval or an edit whose `actionId` names no proposed action, with
an edit that carries no `parameters`, or with a second `request_changes`, by
`centinela_agents/graph.py:resume(graph, alert_id, decision)`. `ejecutar.vigente` reads the KPI on
the day the decision names. The
graph never passes the gate on a decision `apps/api` did not record.

**A transition `apps/api` refuses ends that alert's run**, because the record wins over the
checkpoint. **A decision never expires**: no policy states a deadline, so the interrupt waits.

**The loop to `Analista` is capped at one return**, because each pass is a thinking run on the one
loaded model, and a cause that fails `Estratega` twice is one the data does not support with a
listed action, which is the case manual review exists for.

**A `request_changes` is capped at one per alert**, for the same reason: each pass is a thinking
run on the one loaded model.

**A fallback writes a value, never a route**: the metric's `descripcion` and the entity for the
title, `no_evidence` for the cause, no actions for the proposal, the manual review's one `task` for
`revision_manual`, and no executed action for `Ejecutor`. The manual review's owner comes from the
table of `skills/estratega/acciones.md`, read by `centinela_agents/graph.py:manual_owners(acciones)`
and handed to `compile_tree` as `owners`, so a failed `revision_manual` still reaches the gate with
its task and the alert never stalls.
The tree routes each one, at `explicar.con_evidencia`, `proponer.con_acciones` and
`ejecutar.resultado`.

**A step fails** when its model call fails twice: the call is retried once on a timeout, on a
connection error, or on an output its schema refuses. A step also fails when the alert reaches its
token cap, checked after each call; every model step left on that alert then takes its fallback.
The timeout per call and the token cap are settings of the graph, sized to the machine that runs
Ollama, as the model is. The fallback `reason` of `analista`/`explicar` is one of these, by failure:

| Failure | `reason` |
|---|---|
| timeout | "El análisis no terminó: se agotó el tiempo de respuesta del modelo." |
| token cap | "El análisis no terminó: la alerta alcanzó su tope de tokens." |
| refused schema | "El análisis no terminó: el modelo no devolvió una respuesta válida." |
| any other error: a tool, a connection | "El análisis no terminó: falló una herramienta o la conexión." |

### The state of an alert

| Field | Written by | Read by |
|---|---|---|
| `alert_id`, `simulated_day` | orchestrator | every node, `apps/api` |
| `detection`: metric, entity, `cifra`, `regla`, `fuente_umbral`, severity, `tramo`, `pesos_en_riesgo` | `Vigía` | `Analista`, `Estratega`, orchestrator (order), `apps/api` |
| `title` | `Vigía` | `apps/api` |
| `cause_rejections` | orchestrator, from its input | `Analista` only |
| `proposal_rejections` | orchestrator, from its input and from a `request_changes` | `Estratega` only |
| `cause`, with its `confidence` | `Analista`, or the fallback of `analista`/`explicar` | `Estratega`, orchestrator (`kind`), `apps/api` |
| `same_cause_as` | `Analista` | orchestrator |
| `analyst_returns` | orchestrator | orchestrator |
| `insufficient_cause` | `Estratega` | orchestrator, `Analista` |
| `actions` | `Estratega` | `apps/api`; `Ejecutor` receives the approved one only |
| `decision` | `apps/api`, on resume | orchestrator, `Ejecutor` |
| `rejection_target` | orchestrator | `apps/api` |
| `executed_action` | `Ejecutor` | `apps/api` |
| `merged_into`, `merged_alerts` | orchestrator | `apps/api` |
| `queries` | each agent, from its tool calls | `apps/api` |
| `cost`: prompt tokens, output tokens and model calls, per agent | orchestrator | `apps/api` |
| `failures`: step, `timeout`, `token_cap`, `schema` or `error`, attempts | orchestrator | `apps/api` |
| `status`: the last state `apps/api` accepted | orchestrator | orchestrator |
| `entry`: the leaf the walk of `detectar` reached | orchestrator | orchestrator |
| `earlier_alerts`: the state of each earlier alert | orchestrator, from its input | orchestrator, for `estado.same_cause_as.status` |
| `proposal_returns` | orchestrator | orchestrator |
| `camino`: each node and the branch it took | orchestrator | `apps/api` |
| `events`: a dropped `same_cause_as` | orchestrator | `apps/api` |
| `next_node`, the target a predicate node chose | orchestrator | orchestrator |
| `fin`: the end the walk reached | orchestrator | `apps/api` |

Each output reaches `apps/api` as a log event, typed as `LogEventType` declares:

| Output | `type` | Actor |
|---|---|---|
| a detected alert | `alert` | `vigia` |
| a `Cause`: each `Evidence`, or its `no_evidence`, fallback included | `evidence` | `analista` |
| a merge, naming the alert that remains | `alert` | `analista` |
| the `Actions`, manual review included | `proposal` | `estratega` |
| an executed draft, then its result or its failure | `action`, `result` | `ejecutor` |

The target of a rejection reason joins the `decision` event `apps/api` writes for the person.

### Proposing a transition, not owning it

**The orchestrator proposes each transition an agent causes, and persists none.** Which
transition comes from where, who validates it and why, is the lifecycle on
[`../../apps/api/AGENTS.md`](../../apps/api/AGENTS.md).

### Routing

- **The chat always goes to `Analista`, in chat mode, with no classifier**, because the chat belongs
  to `Analista`. The anchored alert comes from `apps/api` with the question, so `Analista` can
  quote its `actions`. A chat run touches no alert's state and proposes no transition.
- **A rejection reason goes to the classifier** in `skills/orquestador/`, at `fin.rechazada`, the
  only step of the orchestrator that calls the model, thinking off. Its target decides who reads the
  reason on the next run of the same metric:

  | Target | Read by |
  |---|---|
  | `causa` | `Analista` |
  | `propuesta` | `Estratega` |
  | `ambos` | `Analista` and `Estratega` |
  | `ninguno` | no agent; it stays in the `bitácora` |

  `apps/api` keeps the reason with its target, metric and entity, and hands the kept reasons in
  with each run; the orchestrator places each in `cause_rejections` or `proposal_rejections`, so
  each agent learns only from its own mistakes.

### Order

**The alerts of one day run in series, by `pesosAtRisk` from the largest**, ties broken by severity
from `critical` down, then by alert id. In series, because one model is loaded and parallel requests
share its memory and compute, so running alerts side by side buys no speed on this machine. By
pesos, because the largest exposure reaches the inbox first, and because a merge keeps the alert
analysed first, which is the larger: `explicar.destino_analizado` joins this alert to one analysed
before it, and `explicar.destino_nuevo` joins to this alert one the day run has not reached yet. A
chat question does not wait for the day run, only for the model call in course.

### Cost and trace

**After each model call the orchestrator adds Ollama's `prompt_eval_count`, `eval_count` and one
call to the alert's `cost`, under the agent that made it.** A chat answer carries its own cost,
with its anchored alert. `apps/api` persists both.

**Each alert is one Langfuse trace, its id the alert id**, opened when the day run hands the
detection to the alert graph; the resume after a decision adds its spans to the same trace. The
detection of a day is a trace of its own, and so is each chat question.

### What is the orchestrator's, and what is not

| Concern | Owner |
|---|---|
| detecting, and skipping an alert an earlier one covers | `Vigía`, against the earlier alerts `apps/api` hands in |
| the order of the day's alerts | orchestrator |
| the title, the cause, the proposal, the draft | `Vigía`, `Analista`, `Estratega`, `Ejecutor` |
| marking two alerts as one cause | `Analista` |
| merging them | orchestrator |
| walking the tree, compiling a version, refusing an invalid base | orchestrator |
| the manual review `task` | `Estratega`, in code |
| the interrupt at `aprobar.decision` | orchestrator |
| checking that a decision's role may approve and that an edit keeps the action's keys | `apps/api` |
| resuming an alert | `apps/api` calls; the orchestrator refuses a resume with no recorded decision |
| classifying a rejection reason | orchestrator |
| keeping rejection reasons | `apps/api` |
| proposing a transition | orchestrator, or `apps/api` for a person's decision |
| validating and persisting a transition, the `bitácora` | `apps/api` |
| idempotency of an action, masking personal data | `packages/tools` |
| counting cost, opening the trace | orchestrator |
| persisting cost, storing the checkpoint, streaming `AgentStep` | `apps/api` |

## Coverage: every rule has one owner per step

**Every metric in `metricas.yaml` has one owner at each step**, and each owner reads its own file:

| Step | Owner | Reads, per metric |
|---|---|---|
| detect | `Vigía` | its L3 branch of `detectar` in the tree, and the metric's entry in `metricas.yaml`: view, `umbrales`, `fuente_umbral`, `pesos_en_riesgo` |
| explain | `Analista` | `skills/analista/<metric>.md`: its hypotheses and the views that test them |
| propose | `Estratega` | the metric's rows in `skills/estratega/acciones.md`, the closed list of actions with the policy section each comes from |
| execute | `Ejecutor` | the approved action alone |

**A gap is a refusal.** The validator refuses a metric of `metricas.yaml` with no L3 branch in
`detectar`, no file in `skills/analista/`, or no row in `skills/estratega/acciones.md`, so the
base does not load with a gap. Run from this directory: `uv run pytest tests/test_validator.py`.

**The gaps between agents, closed:** the chat belongs to `Analista`; pesos at risk (exposure)
belong to `Vigía` and what an action recovers belongs to `Estratega`; two alerts with one cause are
marked by `Analista` and merged by the orchestrator; a policy passage that gives orders is flagged
by policy search and reported, never obeyed, by `Analista` and `Estratega`; personal data is masked
in `packages/tools` before any agent sees it.

## Rules of this level
- **A route is a branch of the tree.** No code outside the interpreter decides which step an alert
  takes, so a change of route is a change to `arbol/base.yaml`. *The validator refuses an invalid
  base at startup, and `uv run pytest` holds the routes.*

- **The model never produces a number.** Every figure in an explanation or a proposal comes from a
  tool call, and the call travels with the figure as evidence. *No gate holds this.*
- **An agent is given only the tools its section of "What a leaf may use" names.** The graph passes
  the action tools to no model: the node `ejecutar` calls them in code. *No gate holds this.*
- **One cause, one alert**, ranked by pesos at risk.
- **"Not enough evidence" is a complete answer.** An agent that cannot support a claim says so
  instead of guessing, and states its confidence and assumptions when it can.
- **A rejection's reason is kept** and read back by the agent the orchestrator routes it to.
- **Everything is at autonomy level `Propone`** during the hackathon.
- **Every run is traced in Langfuse**, and a change to a skill, a prompt or the tree runs `uv run
  pytest` and the set in [`../../evals/AGENTS.md`](../../evals/AGENTS.md).
