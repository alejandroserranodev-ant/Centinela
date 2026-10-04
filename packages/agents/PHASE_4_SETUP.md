# The agent leaves

This page covers the functions in `centinela_agents/agents/` that the orchestrator hands the
graph as its model leaves. The file keeps its historical name and sits beside
[`AGENTS.md`](./AGENTS.md) because the team keeps the file structure; `AGENTS.md` is the level
page, owns what each agent may decide and use, and links here.

Each leaf is a plain function that receives the provider and returns a dict the graph merges into
the alert's state. Its prompt is written inline in the module: no leaf loads a skill
([`skills/AGENTS.md`](./skills/AGENTS.md)).

| Leaf | Function | Model call | Thinking |
|---|---|---|---|
| `Vigía` writes the title | `centinela_agents/agents/vigia.py:redact_title(provider, state)` | text, temperature 0 | off |
| `Analista` explains the cause | `centinela_agents/agents/analista.py:explain_cause(provider, state, tools)` | structured `Cause`, temperature 0.3 | on |
| `Estratega` proposes actions | `centinela_agents/agents/estratega.py:propose_actions(provider, state, cause, tools)` | structured actions, temperature 0.3 | on |
| `Ejecutor` turns an approved action into a draft | `centinela_agents/agents/ejecutor.py:execute_action(provider, action, decision, tools)` | text for an email body only | off |
| The orchestrator classifies a rejection reason | `centinela_agents/agents/orquestador.py:classify_rejection(provider, reason, cause, actions)` | structured `destino`, temperature 0 | off |

## How the leaves behave

- **Every leaf catches its own exceptions**, logs them and returns a fallback holding only keys
  the state declares: a title built from the metric and entity, a `no_evidence` cause,
  `insufficient_cause`, or no executed action. The classifier's mapping alone also carries the
  exception, as `error`, because the graph reads only its `destino`. The graph's own failure handling ([`AGENTS.md`](./AGENTS.md)) therefore does not see a model
  failure.
- **The model writes the figures.** `Analista`'s evidence and `Estratega`'s impact come back from
  the model with their values and query ids; no leaf calls a tool, because `explain_cause` and
  `propose_actions` read their tools from the registry ([`PHASE_3_SETUP.md`](./PHASE_3_SETUP.md))
  and never call them. This breaks the rule that every figure comes from a tool call.
- **Rejection reasons do not reach the prompts.** The leaves document `cause_rejections` but do
  not read them.
- **The leaves read the alert from the state the graph keeps.** `centinela_agents/state.py:subject(state)`
  returns the metric and the entity of `detection` and the `simulated_day`. The detection holds
  no figure, so the title the model writes carries none.
- **`Ejecutor` builds a task's title and description in code** (`Revisar cliente …`), and writes
  an email body with the model; it calls the action tool when the registry holds one.

## Tests

`uv run pytest tests/test_agents.py` runs each leaf with a mocked provider;
`tests/test_leaves_in_the_graph.py` starts an alert through the orchestrator and checks what each
prompt names and that each leaf returns only declared keys.
