# Spec 3 of 6: how the decision tree grows

**Status:** planned in [`2026-10-04-tree-expansion-plan.md`](./2026-10-04-tree-expansion-plan.md);
where "Amendments the code forced" below departs from a decision, the amendment wins. Runs after
bug spec 1, `orchestrator-runtime`, whose day run, `cost` and `AgentStep` it builds on. **Depends on:** spec 2, `decision-tree`, for the node, the levels and
the validator; spec 1, `normative-foundations`, for the scope this spec implements: any agent
expands the tree inside its own stage, resting only on what the tree already holds, with no
approval before the expansion runs and no agent writing to a database.

**Executed specs.** Specs 1, 2, 4 and 5 are executed and deleted, and a reference below to one of them
reads as a reference to the page that now states it: spec 1, the foundations and the scope of growth,
is [`packages/agents/arbol/AGENTS.md`](../../packages/agents/arbol/AGENTS.md); spec 2, the tree, is
the same page; spec 4, the kernel, is the language in [`data/AGENTS.md`](../../data/AGENTS.md) and the
tools in [`packages/tools/AGENTS.md`](../../packages/tools/AGENTS.md); spec 5, the base KPIs, is
[`data/AGENTS.md`](../../data/AGENTS.md).

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

## Amendments the code forced

The spec predates the orchestrator's runtime and most of today's interpreter. Read against
`packages/agents/centinela_agents/` and `packages/agents/arbol/base.yaml`, each decision below is
replaced as it says, and this section wins over the decision it names.

1. **An expansion is drafted in code, never by a model leaf `expandir`.** *Replaces:* "the leaf
   `<agente>`/`expandir` runs only when a count reaches its setting" and the `expandir.md` row of
   "Pages this spec changes". *Why:* every field of the one move a count can trigger, the leaf, the
   metric and the rows, is fixed by the counted evidence, so a model would only add a way to break
   the fixed criteria; the tree already decides in code where nothing is left to word (`detectar`,
   `revision_manual`). `expandir` leaves `centinela_agents/schema.py:AGENT_DECISIONS`, no
   `expandir.md` is written, and the drafter is `centinela_agents/growth.py`.
2. **A refused draft is dropped and logged at once.** *Replaces:* "the refusal goes back to the
   agent with the criterion named, and a second refusal drops it". *Why:* a code drafter handed the
   same evidence drafts the same move, so a second attempt can only be refused again.
3. **Only `Estratega` drafts in this spec.** *Replaces:* the triggers of `Vigía`, `Analista` and
   `Ejecutor` in the trigger table. *Why:* their evidence does not exist in the tree.
   `Vigía`'s is an approved KPI, which spec 6 defines: `centinela_agents/catalog.py:catalog_from_kernel(answer)`
   fills no `thresholds`, and an approved KPI's catalogue entry names no operator per threshold,
   so its drafter lands with spec 6, on the move this spec builds. `Analista`'s is a confirmed
   hypothesis, and its cause records none, because its leaf tests no hypothesis of
   `skills/analista/<metric>.md`; it stays decided, not built. `Ejecutor`'s is an action ending in
   `nota_manual`, which no alert reaches: `ejecutar.automatizable` lists every type
   `centinela_agents/schema.py:Action` admits, so its count is always zero and is not built.
4. **`Estratega`'s evidence is the rejections `apps/api` stores.** *Replaces:* "the orchestrator
   counts" over evidence it holds. *Why:* the orchestrator keeps nothing between days, and no
   store holds a rejection's target today. `apps/api` stores each rejection the classifier
   targets, with the alert's metric and the ids of the actions it rejected, in `api.rechazos`, and
   hands them to the drafter, which counts them in code. A row is identified by its action id,
   `act-<metric>-r<k>`, the id `centinela_agents/agents/estratega.py:propose_actions(provider, state, cause, sources)`
   already gives it. Handing the reasons to the next run, which `apps/api/AGENTS.md` marks decided,
   stays out of this spec.
5. **"Under that condition" is the alert's metric.** *Replaces:* the open condition of
   `Estratega`'s split. *Why:* the counted evidence shares only the metric, and a node outside
   `detectar` reads no KPI, so the split node reads `estado.detection.metric`, a field the
   interpreter adds to `centinela_agents/state.py:STATE_FIELDS`.
6. **A split leaf differs by the rows it excludes.** *Replaces:* "a new leaf of the same label",
   whose behaviour the spec leaves open. *Why:* a leaf's behaviour is fixed by its agent, its
   decision and its skill file, and only a pull request writes a skill file. The leaf gains
   `excluye`, the action ids `Estratega` must not offer there, and the leaf node hands it to the
   leaf function. A leaf that excludes every row of its metric proposes nothing and calls no model,
   so the alert reaches `revision_manual`.
7. **A split keeps the base's L1 routes by reading through the split.** *Replaces:* "a leaf
   becomes a node". *Why:* every leaf outside `detectar` is reached from an L1 node or a leaf of
   the base, whose routes `centinela_agents/validator.py:base_problems(tree, base)` holds fixed, so
   a split that changes no reference is unreachable and one that changes a reference is refused.
   The split node carries `divide`, the leaf it splits; the move points every reference to the
   leaf at the split node; and the validator reads a reference to a split node as a reference to
   its leaf when it compares L1 and the base's leaves with the base. A second split for the same
   metric splits the leaf the first one added, so the exclusions accumulate and retiring the
   second restores the first.
8. **A new L2 family is a pull request.** *Replaces:* "or a new L2 family" in "add a branch".
   *Why:* `centinela_agents/schema.py:FAMILIES` is code and `centinela_agents/schema.py:level(node_id)`
   reads it. The move adds L3 nodes at the end of an existing family's chain and the metric to the
   family's `en` list, the one change in place, which admits only the new metric's candidate.
9. **A retired node always takes its `no`.** *Replaces:* "stops being walked", which the spec
   leaves to the interpreter. *Why:* a retired split then walks the leaf it split, and a retired
   `detectar` node passes the candidate on as if its rule held no breach. No agent drafts a
   retirement, because no trigger names one; the administrator's retirement is the same move with
   no agent. Retiring the last live branch of a metric is refused as a gap, by the coverage rule
   the validator already holds.
10. **A client's version is a move replayed over the base.** *Replaces:* "a pull-request version
    carries the person who merged it" and the silence on what a merged base does to a client's
    versions. *Why:* the base changes by pull request while expansions live in `apps/api`, so a
    client's tree is the base with its moves replayed in order; a merged base writes a `base` row
    and replays every move, and a move the new base refuses is dropped and logged. Who merged a
    base is in the commit log, where history goes, so the row carries the base's `version` and
    hash instead. `Tree.version` is the row's id.
11. **The tree's version lives on the alert, not on each log row.** *Replaces:* "the tree version on
    each alert event of the `bitácora`". *Why:* a log row reaches its alert through `alerta_id`,
    so a version on every row would store one fact many times. `api.alertas.arbol_version` holds it.
12. **Each `AgentStep` already names its node.** *Replaces:* the decision that it should. *Why:*
    `centinela_agents/graph.py:leaf_node(node, function, ctx, token_cap)` writes `node` on every
    step, and `apps/api` streams it.
13. **The growth runs at the start of each day run.** *Replaces:* the silence on when an expansion
    is drafted. *Why:* rejections arrive with decisions, between days, and a day run is the next
    walk that can use a new version; `apps/api` drafts, persists and then runs the day on the
    newest version, under a lock a retirement also takes.
14. **A missing operand is dropped and logged.** *Replaces:* "filed as a `kpi_gap`". *Why:* the
    `kpi_gap` and its store are spec 6's.
15. **The caps built are the depth of a path and the nodes per stage.** *Replaces:* the cap on
    active approved KPIs per client. *Why:* approved KPIs are spec 6's.
16. **The moves, the criteria and the record are written once, on the tree's page.** *Replaces:*
    the subsection "How the tree grows" on `packages/agents/AGENTS.md` and the expansion move added
    to each agent's output. *Why:* `packages/agents/arbol/AGENTS.md` already holds "How the tree
    grows", and a fact lives in one page; no agent's output gains a move under amendment 1. The
    agents page states only when the orchestrator drafts.
17. **The `ORQ-` cases are `test_orq_*` tests** of `packages/agents/tests/test_expansion.py`,
    `tests/test_growth.py` and `tests/test_orq.py`, as `evals/AGENTS.md` orders for a case that
    needs no model and no `apps/api`.
