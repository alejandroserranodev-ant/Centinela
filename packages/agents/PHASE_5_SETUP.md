# The orchestrator

This page covers `centinela_agents/orchestrator.py`, which binds the agent leaves to the graph
compiler. The file keeps its historical name and sits beside [`AGENTS.md`](./AGENTS.md) because the
team keeps the file structure; `AGENTS.md` is the level page, owns the graph's semantics (stages,
interrupts, failures, routing) and links here.

## What it does

`centinela_agents/orchestrator.py:CentinelaOrchestrator(provider, tools, tree, metrics, catalog, reader, checkpointer, owners, kernel, reasoning_provider)`
maps each leaf of the tree to a function of [`PHASE_4_SETUP.md`](./PHASE_4_SETUP.md), keyed by
agent and decision: `vigia`/`titular`, `analista`/`explicar`, `estratega`/`proponer` and
`revision_manual`, `ejecutor`/`ejecutar` and `nota_manual`. The leaves of `Vigía`, `Analista` and
`Estratega` share one `centinela_agents/evidence.py:Sources` over `kernel`, or over the reader when
no kernel is given, as in the tests; `Analista` and `Estratega` call `reasoning_provider` when one
is given. `revision_manual` is code, over the owners `skills/estratega/acciones.md` names. It hands
that map, the metrics, the KPI catalogue, the reader, a rejection classifier and the checkpointer to
`centinela_agents/graph.py:Compiler`, and compiles the tree once.

- `start(detection, alert_id, day, earlier_alerts, cause_rejections, proposal_rejections)` runs
  `centinela_agents/graph.py:start_alert(graph, detection)` until the graph pauses at the approval gate or ends.
- `is_awaiting_decision(alert_id)` says whether it paused.
- `resume(alert_id, decision)` runs `centinela_agents/graph.py:resume(graph, alert_id, decision)` with the person's decision.
- `get_state(alert_id)` returns the alert's state from the checkpointer.

It adds logging and nothing else; the walk, the gate and the ends are `centinela_agents/graph.py`'s.

## Who builds it

`apps/api/src/centinela_api/agentes.py:get_orchestrator()` builds one per process, with the
provider from `centinela_agents/provider_factory.py:get_provider(provider_name, model_name, thinking)`, the reasoning provider of
`centinela_agents/provider_factory.py:get_reasoning_provider()`, a `ToolRegistry` of the four
action stubs, the kernel's catalogue, reader and call from
`centinela_agents/catalog.py:connect_kernel(env)`, and LangGraph's `InMemorySaver`. That page is
[`../../apps/api/AGENTS.md`](../../apps/api/AGENTS.md).

## The classifier

The orchestrator passes `classify=lambda state: rejection_target(provider, state)`.
`centinela_agents/orchestrator.py:rejection_target(provider, state)` reads the decision's reason,
the cause and the actions from the state, calls
`centinela_agents/agents/orquestador.py:classify_rejection(provider, reason, cause, actions)` and
returns its `destino`, the string `centinela_agents/graph.py:classified(classify, state)` checks
against `REJECTION_TARGETS`.

## Tests

`uv run pytest tests/test_graph_routing.py` compiles small trees and walks them with mocked
leaves; `tests/test_graph.py` and `tests/test_orq.py` test `centinela_agents/graph.py` itself;
`tests/test_orchestrator.py` tests the classifier the orchestrator wires, over a mocked provider.
