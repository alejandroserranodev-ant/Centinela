# The orchestrator

This page covers `centinela_agents/orchestrator.py`, which binds the agent leaves to the graph
compiler. The file keeps its historical name and sits beside [`AGENTS.md`](./AGENTS.md) because the
team keeps the file structure; `AGENTS.md` is the level page, owns the graph's semantics (stages,
interrupts, failures, routing) and links here.

## What it does

`centinela_agents/orchestrator.py:CentinelaOrchestrator(provider, tools, tree, metrics, catalog, reader, checkpointer, owners)`
maps each leaf of the tree to a function of [`PHASE_4_SETUP.md`](./PHASE_4_SETUP.md), keyed by
agent and decision: `vigia`/`titular`, `analista`/`explicar`, `estratega`/`proponer` and
`revision_manual`, `ejecutor`/`ejecutar` and `nota_manual`. It hands that map, the metrics, the
KPI catalogue, the reader, a rejection classifier and the checkpointer to
`centinela_agents/graph.py:Compiler`, and compiles the tree once.

- `start(detection, alert_id, day, earlier_alerts, cause_rejections, proposal_rejections)` runs
  `centinela_agents/graph.py:start_alert(graph, detection)` until the graph pauses at the approval gate or ends.
- `is_awaiting_decision(alert_id)` says whether it paused.
- `resume(alert_id, decision)` runs `centinela_agents/graph.py:resume(graph, alert_id, decision)` with the person's decision.
- `get_state(alert_id)` returns the alert's state from the checkpointer.

It adds logging and nothing else; the walk, the gate and the ends are `centinela_agents/graph.py`'s.

## Who builds it

`apps/api/src/centinela_api/agentes.py:get_orchestrator()` builds one per process, with the
provider from `centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)`, an empty `ToolRegistry`, a reader that returns
demonstration rows, and LangGraph's `InMemorySaver`. That page is
[`../../apps/api/AGENTS.md`](../../apps/api/AGENTS.md).

## The classifier does not classify

The orchestrator passes `classify=lambda state: classify_rejection(provider, state)`, two
arguments to a function that takes four, and the function returns a dict where the compiler
expects a string. `centinela_agents/graph.py:classified(classify, state)` catches the error and
returns `ninguno`, so every rejection reason lands in `ninguno` and reaches no agent.

## Tests

`uv run pytest tests/test_graph_routing.py` compiles small trees and walks them with mocked
leaves; `tests/test_graph.py` and `tests/test_orq.py` test `centinela_agents/graph.py` itself.
