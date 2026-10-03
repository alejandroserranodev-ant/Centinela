# packages/agents: the orchestrator and the four agents

This level holds the reasoning: the orchestrator and `Vigía`, `Analista`, `Estratega` and
`Ejecutor`. It holds no code yet; this page states the domain each agent is built against. What the
challenge asks of each agent is [`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md),
its agents section. How an agent's instructions are written is [`skills/AGENTS.md`](./skills/AGENTS.md).

## Decisions

- **LangGraph is the orchestrator**, because it keeps state per alert and pauses the graph for
  human approval. The approval is an interrupt before `Ejecutor`.
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

## The domain of each agent

**Each agent answers one question, and no agent answers another's.**

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
- **Output:** a detected alert: metric, entity, simulated day, the triggering figure with its
  `queryId`, the broken rule with its `fuente_umbral`, severity, the `tramo` when the metric
  defines `tramos`, and pesos at risk with its `queryId`.
- **Ceiling:** it fires only on a threshold in `metricas.yaml`, evaluated on the simulated day.
  Pesos at risk follow the metric's `pesos_en_riesgo`, computed in SQL. One alert per metric and
  entity, whatever state the earlier one is in; it raises again only when severity rises a tier
  above the highest earlier alert, because a rejected or executed alert whose rule still breaks
  would otherwise return every simulated day.
- **Never:** explains, proposes, reads a policy.

### `Analista` explains, and answers the chat

- **Input:** a detected alert, or a chat question.
- **Tools:** read-only SQL over every view, and policy search.
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

- **Input:** the alert, its `Cause`, and the rejection reasons kept for its metric. On
  `no_evidence`, or when the orchestrator marks `revision_manual`, it proposes one `task` for a
  manual review and nothing else; that branch is code and calls no model, and its `owner` is the
  one `skills/estratega/acciones.md` names for the metric.
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
- **Tools:** none for its model. The node `ejecutar` calls the action tool in code, each a draft or
  a sandbox effect, and the model is called only to write the body of an approved `email_draft`.
- **Output:** an `ExecutedAction`.
- **Ceiling: no discretion.** It passes the approved `parameters` unchanged, keyed by alert and
  action so a second run has no effect. The model writes only the body of an email, with the
  figures it is given and the tone `FIN-POL-004` §6 sets: courteous, written, copied to the seller.
- **Never:** chooses between actions, recomputes, adds a recipient, runs without a recorded decision.

### The orchestrator routes

It is the only part that knows which step an alert is in, and it decides who goes next. It is code,
except one step that classifies a rejection reason. How it routes is the next section.

- **Input:** from `apps/api`, one of three: the simulated day with the metric, entity, severity and
  state of every earlier alert; a recorded decision (the `Decision`, its id, the role that made it
  and when) to resume one alert; or a `ChatQuestion` with its anchored `Alert`, if any. With the
  first two, the rejection reasons `apps/api` keeps for the alert's metric.
- **Tools: none.** Each step that might want one reads its input instead: the order reads
  `pesosAtRisk`, which `Vigía` computed in SQL; the check on `same_cause_as` reads the earlier
  alerts `apps/api` hands in; the classifier reads the reason, the `Cause` with its evidence, and
  the actions with their impact and parameters, each placeholder replaced by its figure. No step
  needs a query, a policy or an action, so the graph gives it no tool.
- **Output:** the state of each alert's graph; an `AgentStep` when an agent's node starts and when
  it ends, with a Spanish `description`, never for its own steps, because `Agent` names the four
  agents only; and, to `apps/api`, the transitions it proposes, the log events, the target of a
  rejection reason, and the cost of each alert.
- **Ceiling:** it moves an alert only along an edge of the graph below, and passes each agent's
  output on unchanged. The only text a person reads that it writes is the fallback of a failed step,
  fixed in this section. It names an alert by metric, entity and simulated day, so a day run twice
  proposes the same ids and `apps/api` refuses the second.
- **Never:** detects, explains, proposes, executes, computes a figure, opens a database connection,
  persists the lifecycle, or resumes an alert past the interrupt without a recorded decision.

## The orchestrator's graph

### Two runs

**The day run is code and keeps no checkpoint.** Advancing the clock hands it the simulated day:
it runs `Vigía`'s detection against the earlier alerts, orders the detected alerts, and runs the
alert graph of each one **in series**, in that order.

**The alert graph is LangGraph, one thread per alert, the alert id as the thread id.** Its host
injects the checkpointer, because an agent never opens a database connection; where the checkpoint
is stored is `apps/api`'s. The checkpoint is working state, never the lifecycle record.

### Nodes and edges

| From | To | When | Proposes to `apps/api` |
|---|---|---|---|
| start | `titular` (`Vigía`, the title) | always | `nueva` |
| `titular` | `analizar` (`Analista`) | always; if the title step fails, the title is the metric's `descripcion` in `metricas.yaml` followed by the entity | `en análisis` |
| `analizar` | `unir` | `same_cause_as` names an earlier alert in `en análisis` or `propuesta` that is not this one | none |
| `analizar` | `absorber` | `same_cause_as` names an alert of the day still in `nueva`, which the day run has not reached and which is therefore the smaller | none |
| `analizar` | `proponer` (`Estratega`) | otherwise; a `same_cause_as` that fails both checks above is dropped and logged | none |
| `analizar` | `revision_manual` | the step fails: the `Cause` is `no_evidence`, `reason` is the fallback for the failure, `queriesReviewed` the queries run so far | none |
| `unir` | end | always: this alert takes `merged_into`, the target adds this id to `merged_alerts` | `unida` |
| `absorber` | `proponer` | always: the named alert takes `merged_into` this alert, which adds it to `merged_alerts`; when the day run reaches it, it is `unida`, its graph does not run, and its title is the fallback of `titular` | `unida`, for the named alert |
| `proponer` | `analizar` | the output is `insufficient_cause` and `analyst_returns` is 0: it becomes 1, and `Analista` receives the cause as `causa_insuficiente` | none; the alert is still `en análisis` |
| `proponer` | `revision_manual` | the output is `insufficient_cause` and `analyst_returns` is 1, or the step fails | none |
| `proponer` | `esperar_decision` | otherwise: one to three `Action`s whose `type` appears in the metric's rows of `skills/estratega/acciones.md` | `propuesta` |
| `revision_manual` (`Estratega`'s manual review, code) | `esperar_decision` | always: one `task`, `impact: null` | `propuesta` |
| `esperar_decision` (the interrupt before `Ejecutor`) | `esperar_decision` | a resume without a recorded decision id: refused, and the refusal returns to `apps/api` | none |
| `esperar_decision` | `ejecutar` (`Ejecutor`) | `approve`; or `edit`, whose `parameters` replace the action's | none; `apps/api` recorded `aprobada` |
| `esperar_decision` | `clasificar_rechazo` | `reject` | none; `apps/api` recorded `rechazada` |
| `clasificar_rechazo` | end | always: the target goes to `apps/api`; if the step fails, the target is `ninguno` | none |
| `ejecutar` | end | `Ejecutor` returns an `ExecutedAction` | `ejecutada` |
| `ejecutar` | end | the step fails: the alert stays `aprobada` and the failure is logged; `apps/api` may resume it again, because actions are idempotent | none |

**A transition `apps/api` refuses ends that alert's run**, because the record wins over the
checkpoint. **A decision never expires**: no policy states a deadline, so the interrupt waits.

**The loop to `Analista` is capped at one return**, because each pass is a thinking run on the one
loaded model, and a cause that fails `Estratega` twice is one the data does not support with a
listed action, which is the case manual review exists for.

**A step fails** when its model call fails twice: the call is retried once on a timeout, on a
connection error, or on an output its schema refuses. A step also fails when the alert reaches its
token cap, checked after each call; every model step left on that alert then takes its fallback.
The timeout per call and the token cap are settings of the graph, sized to the machine that runs
Ollama, as the model is. The fallback `reason` of `analizar` is one of these, by failure:

| Failure | `reason` |
|---|---|
| timeout | "El análisis no terminó: se agotó el tiempo de respuesta del modelo." |
| token cap | "El análisis no terminó: la alerta alcanzó su tope de tokens." |
| refused schema or error | "El análisis no terminó: el modelo no devolvió una respuesta válida." |

### The state of an alert

| Field | Written by | Read by |
|---|---|---|
| `alert_id`, `simulated_day` | orchestrator | every node, `apps/api` |
| `detection`: metric, entity, `cifra`, `regla`, `fuente_umbral`, severity, `tramo`, `pesos_en_riesgo` | `Vigía` | `Analista`, `Estratega`, orchestrator (order), `apps/api` |
| `title` | `Vigía` | `apps/api` |
| `cause_rejections` | orchestrator, from its input | `Analista` only |
| `proposal_rejections` | orchestrator, from its input | `Estratega` only |
| `cause`, with its `confidence` | `Analista`, or the fallback of `analizar` | `Estratega`, orchestrator (`kind`), `apps/api` |
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
- **A rejection reason goes to the classifier** in `skills/orquestador/`, the only step of the
  orchestrator that calls the model, thinking off. Its target decides who reads the reason on the
  next run of the same metric:

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
from `critical` down, then by alert id. In series, because one model is loaded and parallel
requests share its memory and compute, so running alerts side by side buys no speed on this
machine. By pesos, because the largest exposure reaches the inbox first, and because a merge keeps
the alert analysed first, which is the larger: `unir` joins this alert to one analysed before it,
and `absorber` joins to this alert one the day run has not reached yet. A chat question does not
wait for the day run, only for the model call in course.

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
| the manual review `task` | `Estratega`, in code |
| the interrupt before `Ejecutor` | orchestrator |
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
| detect | `Vigía` | the metric's entry in `metricas.yaml`: view, threshold, `fuente_umbral`, `pesos_en_riesgo` |
| explain | `Analista` | `skills/analista/<metric>.md`: its hypotheses and the views that test them |
| propose | `Estratega` | the metric's rows in `skills/estratega/acciones.md`, the closed list of actions with the policy section each comes from |
| execute | `Ejecutor` | the approved action alone |

A metric with no file in `skills/analista/` or no row in `skills/estratega/acciones.md` is a gap.
The command lists the gaps, and prints nothing when every metric is covered:

```bash
for m in $(grep -oP '^  \K[a-z_]+(?=:)' data/metricas.yaml); do
  [ -f packages/agents/skills/analista/$m.md ] || echo "analista: $m"
  sed '/^## /q' packages/agents/skills/estratega/acciones.md | grep -q "^| \`$m\`" || echo "estratega: $m"
done
```

**The gaps between agents, closed:** the chat belongs to `Analista`; pesos at risk (exposure)
belong to `Vigía` and what an action recovers belongs to `Estratega`; two alerts with one cause are
marked by `Analista` and merged by the orchestrator; a policy passage that gives orders is flagged
by policy search and reported, never obeyed, by `Analista` and `Estratega`; personal data is masked
in `packages/tools` before any agent sees it.

## Rules of this level

- **The model never produces a number.** Every figure in an explanation or a proposal comes from a
  tool call, and the call travels with the figure as evidence. *No gate holds this.*
- **An agent is given only the tools its section names.** The graph passes the action tools to no
  model: the node `ejecutar` calls them in code. *No gate holds this.*
- **One cause, one alert**, ranked by pesos at risk.
- **"Not enough evidence" is a complete answer.** An agent that cannot support a claim says so
  instead of guessing, and states its confidence and assumptions when it can.
- **A rejection's reason is kept** and read back by the agent the orchestrator routes it to.
- **Everything is at autonomy level `Propone`** during the hackathon.
- **Every run is traced in Langfuse**, and a change to a skill, a prompt or a graph runs the set in
  [`../../evals/AGENTS.md`](../../evals/AGENTS.md).
