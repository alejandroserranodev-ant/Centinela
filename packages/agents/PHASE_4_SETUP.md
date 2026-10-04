# The agent leaves

This page covers the functions in `centinela_agents/agents/` that the orchestrator hands the
graph as its model leaves. The file keeps its historical name and sits beside
[`AGENTS.md`](./AGENTS.md) because the team keeps the file structure; `AGENTS.md` is the level
page, owns what each agent may decide and use, and links here.

Each leaf is a plain function that receives the provider and returns a dict the graph merges into
the alert's state. Its system prompt is its skill, loaded by
`centinela_agents/skills.py:skill(agent, names)`; its user prompt is the alert and the facts its
code read, with the data last.

| Leaf | Function | Model call | Thinking | `max_tokens` |
|---|---|---|---|---|
| `Vigía` writes the title | `centinela_agents/agents/vigia.py:redact_title(provider, state, sources)` | text, temperature 0 | off | `TITLE_TOKENS` |
| `Analista` explains the cause | `centinela_agents/agents/analista.py:explain_cause(provider, state, sources)` | structured, `CAUSE_SCHEMA`, temperature 0 | on | `CAUSE_TOKENS` |
| `Estratega` proposes actions | `centinela_agents/agents/estratega.py:propose_actions(provider, state, cause, sources)` | structured, `PROPOSAL_SCHEMA`, temperature 0 | on | `PROPOSAL_TOKENS` |
| `Ejecutor` turns an approved action into a draft | `centinela_agents/agents/ejecutor.py:execute_action(provider, action, decision, tools)` | text for an email body only | off | `EMAIL_TOKENS` |
| The orchestrator classifies a rejection reason | `centinela_agents/agents/orquestador.py:classify_rejection(provider, reason, cause, actions)` | structured `destino`, temperature 0 | off | none |

## How the leaves behave

- **A leaf raises, and the graph takes its fallback.** A model error, a timeout, or an output the
  leaf refuses, `centinela_agents/failures.py:SchemaRefused`, reaches
  `centinela_agents/graph.py:leaf_node(node, function, ctx, token_cap)`, which writes the fallback and records
  the failure. The classifier alone catches its own exceptions and returns `ninguno`.
- **The code reads the figures; the model cites them.** `Vigía` hands the compared columns and
  `pesos_en_riesgo` as `{0}`, `{1}`; `Analista` hands numbered facts `f1`, `f2` and receives refs,
  which `centinela_agents/evidence.py:Ledger.figures(refs)` turns into figures with their
  `queryId`; `Estratega` receives row refs and builds each action in code.
- **A figure written outside a placeholder is refused** by
  `centinela_agents/evidence.py:stray_digits(text, allowed)`: a title or a cause sentence with one
  fails its leaf, a claim with one is dropped, and an action with one is not proposed. Digits of
  the entity's identifiers and of the simulated day are allowed.
- **Rejection reasons reach the prompts.** `Analista` reads `cause_rejections` and
  `insufficient_cause`, `Estratega` reads `proposal_rejections`.
- **`Ejecutor` builds a task's title and description in code** (`Revisar cliente …`), and writes
  an email body with the model over a masked prompt; it calls the action tool when the registry
  holds one.

## Tests

`uv run pytest tests/test_agents.py` runs each leaf with a mocked provider over a fake kernel;
`tests/test_leaves_in_the_graph.py` starts an alert through the orchestrator and checks what each
prompt names and that each leaf returns only declared keys; `uv run pytest -m modelo` runs
`tests/test_modelo.py`, each leaf against the model and the kernel.
