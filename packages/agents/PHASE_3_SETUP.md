# The tool stubs

This page covers the tool interfaces `packages/agents` declares for its leaves and the stubs that
implement them. The file keeps its historical name and sits beside [`AGENTS.md`](./AGENTS.md)
because the team keeps the file structure; `AGENTS.md` is the level page and links here.

The tools an agent calls belong to `packages/tools`
([`../tools/AGENTS.md`](../tools/AGENTS.md)). The leaves read its kernel directly, through
`centinela_agents/evidence.py`; these interfaces re-declare the other tools inside
`packages/agents`, and no stub opens a database connection.

## The interfaces

`centinela_agents/tools.py` declares one abstract class per tool and the dataclass it returns:

- `SqlVistasProvider.query(view_name, filters, simulated_day)`, returning a `SqlQuery` with rows
  and a `queryId`;
- `BuscarPoliticaProvider.search(query, top_k)`, returning `PolicyPassage`s;
- `CalcularImpactoProvider.calculate(formula_name, entidad, simulated_day)`, returning an
  `ImpactResult`;
- `EmailDraftTool`, `TaskTool`, `PurchaseOrderDraftTool` and `PriceChangeDraftTool`, each with an
  `execute(...)` that returns a draft result.

`centinela_agents/tools.py:ToolRegistry` holds one optional instance of each, and
`get_tools_for_agent(agent)` names which tools each agent may use: none for `vigia`, SQL and
policy search for `analista`, those plus impact for `estratega`, the four action tools for
`ejecutor`. `apps/api` builds the registry with the four action stubs and nothing else, so the
SQL, policy and impact tools are `None` at runtime and no leaf calls them.

## The stubs

- `centinela_agents/sql_vistas.py:SqlVistasStub` returns no rows.
- `centinela_agents/buscar_politica.py:BuscarPoliticaStub` returns no passages, although it holds
  a policy table it never reads.
- `centinela_agents/calcular_impacto.py:CalcularImpactoStub` returns a value of `0` for every known
  formula, with an assumption saying so, and an error for an unknown one; the SQL it holds per
  formula never runs.
- `centinela_agents/action_tools.py` holds `EmailDraftStub`, `TaskStub`, `PurchaseOrderDraftStub`
  and `PriceChangeDraftStub`, which keep nothing and return a draft named by
  `centinela_agents/action_tools.py:stable_id(prefix, parts)` over its inputs, so two calls for the
  same action return the same id.

`apps/api` constructs the action stubs; only the tests construct the other three.

## Tests

`uv run pytest tests/test_tools.py` checks the stubs and the registry.
