# Spec 3 of 6: how the decision tree grows

**Status:** pending its plan. **Depends on:** spec 2, `decision-tree`, for the node, the levels and
the validator; spec 1, `normative-foundations`, for the scope this spec implements: any agent
expands the tree inside its own stage, resting only on what the tree already holds, with no
approval before the expansion runs and no agent writing to a database.

## Why

Centinela adapts to a client by changing its tree, and it adapts fastest when the agents that walk
the tree change it themselves. That is safe only if every expansion is held by criteria fixed in
advance and checked by code, never by an agent's judgement, and if no expansion can open a path
around a person's approval.

## Decisions

- **L0 and L1 are closed to expansion**, by agent and by self-expansion alike; they change by pull
  request only. The laws and the stages come from the standards of spec 1, not from a client.
- **An expansion is one of three moves, and no other:**

  | Move | What it does | Why it is safe |
  |---|---|---|
  | add a branch | a new L3 node under an existing L2 family of the agent's stage, or a new L2 family | no existing path changes |
  | split a leaf | a leaf of the agent's own label becomes a node whose one branch is the old leaf and whose other is a new leaf of the same label | the old behaviour survives on one branch |
  | retire a branch | an L2 or L3 branch is marked `retirado` with a reason and stops being walked; it stays in the version | the `bitácora` of past alerts still names the nodes it walked |

  An agent never edits or deletes a node in place, because an edit is a delete plus an add with no
  record that the old path existed.
- **An agent expands only inside its own stage, with leaves of its own label.** `Vigía` in
  `detectar` and `medir`, `Analista` in `explicar`, `Estratega` in `proponer`, `Ejecutor` in
  `ejecutar`. Stages `aprobar` and `cerrar` have no agent, so they grow by pull request only.
- **An expansion is triggered by repetition counted in code, never by a single run.** The
  orchestrator counts, per agent and stage, the recurring evidence the expansion would act on, and
  the leaf `<agente>`/`expandir` runs only when a count reaches its setting:

  | Agent | Recurring evidence | Typical move |
  |---|---|---|
  | `Vigía` | an approved KPI (spec 6) that no `detectar` node reads yet | add a branch that compares it with its `umbral` |
  | `Analista` | the same hypothesis of a skill confirmed for the same metric across N alerts | split its `explicar` leaf so that metric's alerts test that hypothesis first |
  | `Estratega` | the same rejection target `propuesta` with the same action row across N alerts | split its `proponer` leaf so the rejected row is not offered under that condition |
  | `Ejecutor` | the same action type ending in `nota_manual` across N alerts | none it can make alone: a missing tool is a pull request to `packages/tools`; the count is reported |

  N is a setting of the method, like a window of an `analista/` skill; it decides when an
  expansion is drafted, never whether an alert fires.
- **No person approves an expansion before it runs**, because every move keeps every path to an
  `Ejecutor` leaf through `aprobar.decision` and `ejecutar.vigente`, which the validator checks.
  The administrator sees every expansion in the `bitácora` and may retire it at any time; a retired
  expansion's evidence must reach N again before it is drafted anew.
- **An expansion is an output, never a write.** The agent returns the move; the orchestrator runs
  the validator on the resulting version; `apps/api` persists the version and writes it to the
  `bitácora`. The base stays in `packages/agents/arbol/`; a client's versions live in `apps/api`'s
  schema, keyed by client.
- **A pull request is the other way the tree grows**, for the base, for L0 and L1, and for the
  registry, and it passes the same validator and the evals.

## The fixed criteria

An expansion is persisted only when every row holds.

| Criterion | Held by |
|---|---|
| the move is one of the three, inside the agent's stage, with leaves of its label | the validator, against the agent that returned it |
| each new node's `fundamento` is an entry of `fundamentos.yaml` | the validator |
| each new node passes the atomicity test of spec 1 | the validator |
| each new node's operand is a KPI of the client's catalogue (base or approved) or a declared state field; an expansion that needs a measure the catalogue lacks is dropped and its need filed as a `kpi_gap` (spec 6) | the validator |
| each new threshold is an `umbral` naming a `metricas.yaml` entry, whose `fuente_umbral` quotes a document | the validator |
| each new leaf's agent keeps the tools it has | the validator, against the tool list per agent on `packages/agents/AGENTS.md` |
| every path to an `Ejecutor` leaf passes `aprobar.decision` and `ejecutar.vigente` | the validator |
| the version stays under the caps of spec 1: path depth, nodes per stage | the validator |
| the evidence count reached N | the orchestrator, before the leaf `expandir` runs |
| L0 and L1 hash to the base | the validator |

The validator refuses an expansion once; the refusal goes back to the agent with the criterion
named, and a second refusal drops it and logs it.

## The record of a version

Each version carries `version`, its parent version, the client, the move, the agent and the
evidence ids that triggered it, the hash of L0 and L1, and the date; a pull-request version carries
the person who merged it instead of the agent. The alert's state gains `arbol_version`, written by
the orchestrator and persisted by `apps/api`, and each `AgentStep` names the node id that started
it, so "how I got here" shows the path, not just the queries.

## Pages this spec changes

| Page | Change |
|---|---|
| `packages/agents/AGENTS.md`, "The decision tree" (written by spec 2) | a subsection "How the tree grows": self-expansion, the three moves, the triggers per agent, the fixed criteria, the version record |
| `packages/agents/AGENTS.md`, each agent in "What a leaf may use" | its output gains an expansion move, inside its stage |
| `packages/agents/AGENTS.md`, "The state of an alert" | a row: `arbol_version`, written by the orchestrator, read by `apps/api` |
| `packages/agents/skills/` | one `expandir.md` per agent directory, written by the rules of `skills/AGENTS.md`, and loaded only at the leaf `expandir`, by the loading rule spec 2 writes |
| `apps/api/AGENTS.md` | the store of tree versions per client, handed to each run; the administrator's retirement of an expansion; the tree version on each alert event of the `bitácora` |
| `apps/web/AGENTS.md` | `Configuración` lists the client's expansions, newest first, each with its evidence and a "Retirar" action |
| `evals/AGENTS.md` | `ORQ-` cases: an expansion outside its agent's stage (refused); a `fundamento` absent from the registry (refused); a split leaf whose old branch still produces the earlier output; a move that bypasses `aprobar` (refused); evidence below N (no expansion); a retired expansion not drafted again before N; a change to an L1 node (refused) |
| `docs/guide/chapters/decision-tree.md` | the section on how the tree grows shrink to a link to the level page this spec writes them into; the diagrams stay in the chapter, each captioned `Draws:` with that page's new section, and the chapter's warning box drops what this spec implements |

## Acceptance

- The validator refuses one planted violation of every criterion it holds.
- A split leaf, run on a simulated day where the new predicate is false, produces the output the
  unsplit tree produced on that day.
- No path of the code lets an agent persist a version: `apps/api` is the only writer.
