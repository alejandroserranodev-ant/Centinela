# What exists today

Every claim in this guide sits in one of three states, and this page is where they are sorted:

| State | Means | Where it is stated |
|---|---|---|
| *Implemented* | a file a program reads exists and does what its page says | the code inventory below this page, derived from the published commit; and the sentence of [the project page](../../../AGENTS.md) that says which parts hold code |
| *Decided, not implemented* | a level page or a chapter of this guide states the decision the code is written against, and no code exists yet | each level page, and the chapters marked with a warning |
| *Roadmap* | the project chooses not to build it for the hackathon, or has not decided it | the list at the end of this page, each item linked to the page that says so |

The inventory counts source files per part. A part whose row shows none holds only the decisions its
page states, however complete that page reads. **A page written in the present tense describes the
design, not running code.**

## By part

| Part | What it decides | Pending design owned by this guide |
|---|---|---|
| `data` | [data](../../../data/AGENTS.md): the dataset, the semantic layer, the clock, the generator | the kernel's language and `05_kpis.generated.sql` ([the KPI kernel](./kpi-kernel.md)) |
| `packages/tools` | [packages/tools](../../../packages/tools/AGENTS.md): SQL, policy search, `calcular_impacto`, actions | the kernel's compiler and its tools |
| `packages/agents` | [packages/agents](../../../packages/agents/AGENTS.md): the agents, the decision tree and its interpreter; [its skills](../../../packages/agents/skills/AGENTS.md) | the growth of the decision tree ([the decision tree](./decision-tree.md)); `proponer_kpi` |
| `apps/api` | [apps/api](../../../apps/api/AGENTS.md): the clock, the lifecycle, roles, the `bitácora` | the store of tree versions per client, the KPI catalogue and its lifecycle |
| `apps/web` | [apps/web](../../../apps/web/AGENTS.md): the inbox, its skin, the simulated API it runs on | the KPI catalogue and proposals, and the expansions list, in `Configuración` |
| `evals` | [evals](../../../evals/AGENTS.md): the case format and the cases of each agent | cases for the tree's growth and the kernel |

## Roadmap

- **What the brief puts out of scope**, presented in the pitch as roadmap: the MVP scope section of
  [The challenge](../../../docs/challenge/AGENTS.md).
- **Autonomy past `Propone`**: every action type stays at `Propone` during the hackathon
  ([The challenge](../../../docs/challenge/AGENTS.md)).
- **`cerrar`'s effectiveness review** of an executed alert ([the decision tree](./decision-tree.md)).
- **The questions no page owns yet**, listed as still undecided on
  [the project page](../../../AGENTS.md).
- **The debts filed against the tree**, each with what it costs: [Debts](../../../DOUBTS.md).
