# What runs and what is decided

Every claim in this guide sits in one of three states, and this page is where they are sorted:

| State | Means | Where it is stated |
|---|---|---|
| *Built* | a file a program reads exists and does what its page says | each level page, which says what runs there; and the code inventory below this page, derived from the published commit |
| *Decided, not built* | a level page or a chapter of this guide states the decision the code is written against, and no code exists | each section that opens with a warning box saying so, on a level page or in a chapter |
| *Roadmap* | the project chooses not to build it for the hackathon, or has not decided it | the list at the end of this page, each item linked to the page that says so |

The inventory counts source files per part. A part whose row shows none holds only the decisions its
page states, however complete that page reads. **A page written in the present tense describes the
design, and its warning boxes say which part of it runs.**

## By part

| Part | What runs | What it decides | Pending design owned by this guide |
|---|---|---|---|
| `data` | the schema, the load, the views and the generator | [data](../../../data/AGENTS.md): the dataset, the semantic layer, the clock, the kernel's language, the base KPIs | none |
| `packages/tools` | the KPI kernel: its compiler, guards and tools, and the generator of the base KPIs | [packages/tools](../../../packages/tools/AGENTS.md): the kernel, then SQL over the views, policy search, `calcular_impacto` and the actions | none |
| `packages/agents` | the validator of the decision tree, the walk of `detectar`, the catalogue the kernel hands the tree, the compiler of the tree to a graph, and model leaves that read the kernel | [packages/agents](../../../packages/agents/AGENTS.md): the agents and the orchestrator; [its skills](../../../packages/agents/skills/AGENTS.md); [the tree](../../../packages/agents/arbol/AGENTS.md) | the moves and the triggers of the tree's growth ([the decision tree](./decision-tree.md)); `proponer_kpi` ([the KPI kernel](./kpi-kernel.md)) |
| `apps/api` | the endpoints, the clock, the lifecycle and the `bitácora`, with the agents run in its process over the kernel | [apps/api](../../../apps/api/AGENTS.md): the clock, the lifecycle, roles, the `bitácora` | the KPI catalogue and its lifecycle ([the KPI kernel](./kpi-kernel.md)) |
| `apps/web` | the screens, on `apps/api` through a fetch client | [apps/web](../../../apps/web/AGENTS.md): the inbox, its skin, its draft contract with `apps/api` | the KPI catalogue and proposals, and the expansions list, in `Configuración` |
| `evals` | nothing here; its runnable cases are tests in `packages/agents` and `packages/tools` | [evals](../../../evals/AGENTS.md): the case format and the cases of each agent | cases for the tree's growth |
| `scripts/check` | the gates that hold the documentation to the tree | [scripts/check](../../../scripts/check/AGENTS.md) | none |
| `docs/guide` | `docs/guide/publish.py`, which builds and publishes this guide | [docs/guide](../AGENTS.md) | none |

## Roadmap

- **What the brief puts out of scope**, presented in the pitch as roadmap: the MVP scope section of
  [The challenge](../../../docs/challenge/AGENTS.md).
- **Autonomy past `Propone`**: every action type stays at `Propone` during the hackathon
  ([The challenge](../../../docs/challenge/AGENTS.md)).
- **The questions no page owns**, listed as undecided on [the project page](../../../AGENTS.md).
- **The debts filed against the tree**, each with what it costs: [Debts](../../../DOUBTS.md).
