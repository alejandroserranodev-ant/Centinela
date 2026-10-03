# How an alert crosses the parts

This chapter follows one alert through the monorepo, so that each level page after it has a place
in one picture. It states no rule of its own: each step names the page that owns it, and each
diagram names the section it draws.

> **Decided, not implemented.** The journey below is what the level pages decide. Which part of
> it runs as code today is [What exists today](./status.md).

## The chain

```mermaid
flowchart LR
  web["apps/web<br/>the decision inbox"] --> api["apps/api<br/>clock, lifecycle, bitácora"]
  api --> agents["packages/agents<br/>orchestrator and agents"]
  agents --> tools["packages/tools<br/>the closed list of tools"]
  tools --> data["data<br/>dataset, views, metricas.yaml, policies"]
  evals["evals"] -. drives .-> api
  evals -. checks answers against .-> data
```

*Draws: `AGENTS.md` § How the parts connect*

Each arrow is a call, and nothing calls back up the chain. The rule and what holds it are on
[the project page](../../../AGENTS.md); what each part decides is its own page under *The levels*.

## One alert, from the clock to the log

```mermaid
sequenceDiagram
  autonumber
  actor P as Person
  participant W as apps/web
  participant A as apps/api
  participant O as Orchestrator
  participant V as Vigía
  participant N as Analista
  participant E as Estratega
  participant X as Ejecutor
  participant T as packages/tools
  P->>W: advance the simulated day
  W->>A: POST /simulacion/avanzar
  A->>O: day run: the simulated day, earlier alerts, kept rejection reasons
  O->>V: detect
  V->>T: read each measure on the simulated day
  T-->>V: figures, each with its query
  V-->>O: detected alerts, against the thresholds of metricas.yaml
  Note over O: one alert at a time, largest pesos at risk first
  O-->>A: proposes nueva, then en análisis
  O->>N: explain
  N->>T: query views, search policies
  N-->>O: a Cause with evidence, or no_evidence
  O->>E: propose
  E->>T: calcular_impacto
  E-->>O: one to three Actions with impact
  O-->>A: proposes propuesta, then pauses before Ejecutor
  A-->>W: SSE: the alert reaches the inbox
  P->>W: approve, edit or reject with a reason
  W->>A: POST /alertas/{id}/decision
  A->>A: checks the role, records aprobada or rechazada
  A->>O: resumes the alert with the recorded decision
  O->>X: execute the approved action
  X->>T: a draft or sandbox action
  X-->>O: ExecutedAction
  O-->>A: proposes ejecutada
  Note over A: every step lands in the bitácora
```

*Draws: `AGENTS.md` § How the parts connect; `packages/agents/AGENTS.md` § The orchestrator's graph*

The steps, each with the page that owns it:

- **The clock.** `apps/api` owns the simulated day, which replaces `fecha_corte()`
  ([apps/api](../../../apps/api/AGENTS.md)); which views ignore that day is the clock section of
  [data](../../../data/AGENTS.md).
- **Detection.** `Vigía` fires on written thresholds only, one alert per metric and entity, and
  computes pesos at risk in SQL ([packages/agents](../../../packages/agents/AGENTS.md)).
- **Explanation.** `Analista` proves a cause by entity, time and direction, or answers that the
  evidence is not enough; when its cause already explains another open alert, the orchestrator
  merges the two.
- **Proposal.** `Estratega` picks only actions its skill lists for the metric, and every amount comes
  from `calcular_impacto` ([packages/tools](../../../packages/tools/AGENTS.md)).
- **Approval.** The graph pauses before `Ejecutor` and resumes only with a decision `apps/api`
  recorded; a rejection's reason is kept and routed back to the agent it concerns.
- **Execution.** `Ejecutor` turns the approved action into a draft, unchanged, and a second run has
  no effect.
- **The log.** Every step lands in the `bitácora`, which `apps/api` owns and nothing updates.

## The lifecycle of an alert

```mermaid
stateDiagram-v2
  state "en análisis" as en_analisis
  [*] --> nueva: Vigía detects
  nueva --> en_analisis: the title is written
  en_analisis --> propuesta: Estratega proposes
  en_analisis --> unida: merged into another alert
  propuesta --> aprobada: a person approves or edits
  propuesta --> rechazada: a person rejects, with a reason
  aprobada --> ejecutada: Ejecutor returns its result
  unida --> [*]
  rechazada --> [*]
  ejecutada --> [*]
```

*Draws: `apps/api/AGENTS.md` § Decisions*

The orchestrator proposes each transition an agent causes, and `apps/api` proposes the ones a
person causes; `apps/api` validates and persists all of them, because it is the only part with
storage. `unida` is the one state the brief's lifecycle lacks, and
[apps/api](../../../apps/api/AGENTS.md) says why it exists.
