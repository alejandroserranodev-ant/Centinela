# packages/agents: the orchestrator and the four agents

This level holds the reasoning: the orchestrator and `Vigía`, `Analista`, `Estratega` and
`Ejecutor`. It holds no code yet; this page states the decisions the code is written against. What
each agent does is [`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its agents
section.

## Decisions

- **LangGraph is the orchestrator**, because it keeps state per alert and pauses the graph for
  human approval. The approval is an interrupt before `Ejecutor`.
- **Two model tiers**: a large Claude model where an agent reasons (`Analista`, `Estratega`), a fast
  one where it classifies or routes. Which model a step uses is decided per step, not per agent.
- **`Vigía` detects with rules and statistics, not with a model.** The thresholds are the ones in
  `metricas.yaml` (see [`../../data/AGENTS.md`](../../data/AGENTS.md)) plus z-score and trend; the
  model, where used, only words the finding.

## Rules of this level

- **The model never produces a number.** Every figure in an explanation or a proposal comes from a
  tool call, and the call travels with the figure as evidence. *No gate holds this.*
- **Only `Ejecutor` acts**, only after approval, and only with draft or sandbox tools.
- **One cause, one alert.** `Vigía` groups findings that share a cause before raising them, and
  alerts are ranked by pesos at risk.
- **"Not enough evidence" is a complete answer.** An agent that cannot support a claim says so
  instead of guessing, and states its confidence and assumptions when it can.
- **A rejection's reason is kept** and read back by the agents on later alerts of the same kind.
- **Everything is at autonomy level `Propone`** during the hackathon.
- **Sensitive data is masked before it reaches a model.**
- **Every run is traced in Langfuse**, and a change to a prompt or a graph runs the set in
  [`../../evals/AGENTS.md`](../../evals/AGENTS.md).
