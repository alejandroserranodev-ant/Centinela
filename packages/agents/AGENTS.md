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

- **Input:** the simulated day.
- **Tools:** read-only SQL over the views `metricas.yaml` names, filtered by the simulated day.
  No policy search: its thresholds are already in `metricas.yaml`.
- **Output:** a detected alert: metric, entity, simulated day, the triggering figure with its
  `queryId`, the broken rule with its `fuente_umbral`, severity, the `tramo` when the metric
  defines `tramos`, and pesos at risk with its `queryId`.
- **Ceiling:** it fires only on a threshold in `metricas.yaml`, evaluated on the simulated day.
  Pesos at risk follow the metric's `pesos_en_riesgo`, computed in SQL. One open alert per metric
  and entity; it raises again only when severity rises a tier.
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
  `no_evidence` it proposes one `task` for a manual review and nothing else.
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
- **Tools:** only the action tools, each a draft or a sandbox effect.
- **Output:** an `ExecutedAction`.
- **Ceiling: no discretion.** It passes the approved `parameters` unchanged, keyed by alert and
  action so a second run has no effect. The model writes only the body of an email, with the
  figures it is given and the tone `FIN-POL-004` §6 sets: courteous, written, copied to the seller.
- **Never:** chooses between actions, recomputes, adds a recipient, runs without a recorded decision.

### The orchestrator

- **Owns the transitions** up to `propuesta`, merges alerts `Analista` marks as one cause, and holds
  the interrupt before `Ejecutor`.
- **Classifies a rejection reason** as about the cause, kept for `Analista`, or about the proposal,
  kept for `Estratega`, so each agent learns only from its own mistakes.

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
  grep -q "^| \`$m\`" packages/agents/skills/estratega/acciones.md || echo "estratega: $m"
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
- **An agent is given only the tools its section names.** The graph does not pass the action tools
  to any agent but `Ejecutor`. *No gate holds this.*
- **One cause, one alert**, ranked by pesos at risk.
- **"Not enough evidence" is a complete answer.** An agent that cannot support a claim says so
  instead of guessing, and states its confidence and assumptions when it can.
- **A rejection's reason is kept** and read back by the agent the orchestrator routes it to.
- **Everything is at autonomy level `Propone`** during the hackathon.
- **Every run is traced in Langfuse**, and a change to a skill, a prompt or a graph runs the set in
  [`../../evals/AGENTS.md`](../../evals/AGENTS.md).
