# Spec 2 of 6: the decision tree

**Status:** pending its plan. **Depends on:** spec 1, `normative-foundations`, for the vocabulary
(rule, node, `fundamento`, registry, leaf, gate, self-expansion, atomicity), the laws of level L0,
and the scope: who may grow the tree and how far.

## Why

Today the routing of an alert is spread over five sections of `packages/agents/AGENTS.md`: one per
agent and the orchestrator's table of nodes and edges. A client who needs one more decision has to
edit prose in several places, and nothing proves the edit leaves every path with an end. The tree
replaces that with one artefact that is **data, validated by code, and walked by a deterministic
interpreter**. The model acts only at a leaf.

## Decisions

- **The tree's base lives in `packages/agents/arbol/`, as YAML, beside the registry
  `fundamentos.yaml`**, because routing is the orchestrator's concern and the orchestrator lives in
  `packages/agents`. YAML matches `data/metricas.yaml`, which the tree's predicates read. A client's
  self-expansions are not files: `apps/api` persists them and hands the client's current version
  with each run (spec 3), because no agent writes anywhere (spec 1).
- **The tree compiles to the LangGraph graph.** Each leaf becomes a graph node, each predicate
  becomes the function of a conditional edge, and the approval interrupt sits before every
  `Ejecutor` leaf. LangGraph stays, because it keeps state per alert and pauses for approval; the
  tree decides the shape it runs. The base is validated at startup, and an invalid base stops the
  start; each run compiles the version `apps/api` hands in, cached by version, and a version the
  validator refuses is never handed in, because spec 3 validates it before it is persisted.
- **The orchestrator becomes the tree's interpreter and keeps nothing else to decide.** What
  remains of each agent's section is what a leaf may *use* (its tools, its input, its output, its
  ceiling), because a tool is a permission, not a route. Every *route* is a branch of the tree.
- **A predicate holds no literal threshold.** It names the metric whose `umbral_alerta` in
  `metricas.yaml` it applies, so a threshold stays in one place.
- **The diagram's flow, the one the team drew for a late payer, is the tree's first walkthrough
  and its first eval case.** Its gates enter the tree as the decisions below.

## The node

```yaml
version: 1
nodos:
  - id: detectar.cartera.vencida
    fundamento: fin-pol-004.s4
    predicado: { lee: kpi.saldo_vencido.max_dias_vencido, op: ">", umbral: saldo_vencido }
    si: hoja.vigia.titular
    no: fin.sin_alerta
  - id: hoja.vigia.titular
    hoja: { agente: vigia, decision: titular, skill: vigia/contrato.md }
    sigue: explicar.raiz
```

| Field | Rule |
|---|---|
| `id` | unique; its first segment is the stage of spec 1 (`detectar`, `explicar`, `proponer`, `aprobar`, `ejecutar`, `cerrar`, `medir`), or `hoja`, or `fin` |
| `fundamento` | the id of exactly one entry of `fundamentos.yaml`; required on every node, absent on a leaf, which inherits its parent's |
| `predicado.lee` | a KPI column of the kernel (`kpi.<metric>.<column>`) or a field of the alert's state (`estado.cause.kind`, `estado.decision.kind`, `estado.analyst_returns`) |
| `predicado.op` | one of `>`, `>=`, `<`, `<=`, `=`, `!=`, `en` (membership in a closed list written in the node), `existe` |
| `predicado.umbral` or `predicado.valor` | `umbral` names a metric of `metricas.yaml`; `valor` is a literal and is admitted only for a state field, never for a KPI |
| `si`, `no` | both required, each the id of a node, a leaf or an end |
| `hoja` | `agente` (`vigia`, `analista`, `estratega`, `ejecutor`), `decision` from that agent's closed list, `skill` a path under `packages/agents/skills/` |
| `sigue` | on a leaf only: the node the walk continues at once the agent returns |

**The closed list of decisions per agent:**

| Agent | Decisions |
|---|---|
| `vigia` | `detectar` (code), `titular`, `proponer_kpi` (spec 6), `expandir` (spec 3) |
| `analista` | `explicar`, `responder_chat`, `expandir` |
| `estratega` | `proponer`, `revision_manual` (code), `expandir` |
| `ejecutor` | `ejecutar`, `nota_manual`, `expandir` |

## The levels

| Level | Holds | Changed by |
|---|---|---|
| L0 | the laws of spec 1, checked on every step | a pull request to the root page only |
| L1 | one node per stage, in the order of spec 1 | a pull request only |
| L2 | one branch per metric family: `cartera`, `margen`, `inventario`, `comercial`, `abastecimiento`, `clientes` | the stage's agent by self-expansion, or a pull request (spec 3) |
| L3 | the nodes of one metric and their leaves | the stage's agent by self-expansion, or a pull request (spec 3) |

## What today's graph becomes

Every row of the table "Nodes and edges" in `packages/agents/AGENTS.md` becomes a node or a leaf.
Representative rows:

| Today | In the tree |
|---|---|
| `analizar` → `unir` when `same_cause_as` names an open alert | node `explicar.misma_causa`, `lee: estado.same_cause_as`, `op: existe`, `fundamento: iso9001.10.2.1.b.3` |
| `proponer` → `analizar` when `insufficient_cause` and `analyst_returns` is 0 | two nodes: `proponer.causa_insuficiente` (`existe`), then `proponer.retorno_disponible` (`analyst_returns` `=` 0); two predicates, so two nodes |
| `esperar_decision` → `ejecutar` on `approve` or `edit` | gate `aprobar.decision`, `lee: estado.decision.kind`, `op: en`, list `[approve, edit]` |

The fallbacks of a failed step, the token cap, the retry and the order of a day's alerts are
settings of the interpreter, not nodes, because they decide *how* a step runs, not *which* step
runs. They stay on `packages/agents/AGENTS.md`.

## The gates the diagram adds

| Diagram | Decision | Reason |
|---|---|---|
| "¿Tiene más dudas?" → the user asks in the chat | no node: the chat is a route of its own to `analista`/`responder_chat`, and it touches no alert's state | the chat belongs to `Analista` and changes no alert's state, as it does today |
| "¿Solicita sugerencias?" → incorporate the user's or the administrator's prompt | no node; the question goes to `responder_chat`, which quotes `Estratega`'s proposal or says there is none | a person's text is a question, never an order that widens a closed list (law L0) |
| "¿Continuar al Estratega?" | no gate: `Estratega` runs right after `Analista`, and "continue" is the person opening the proposals | the brief's principle: the problem reaches the user "with a proposal ready to approve" |
| "¿Recargar propuestas?" and "Solicitar cambios" | a new decision, `request_changes`, with a reason; gate `aprobar.recargar` sends the alert back to `proponer` with the reason in `proposal_rejections`, once per alert | the diagram's loop back to `Estratega`; capped at one for the reason today's return to `Analista` is capped |
| "¿Aprobar?" approve / reject | the existing decisions `approve`, `edit`, `reject` | unchanged |
| "¿Acción automatizable?" | node `ejecutar.automatizable`, `lee: estado.action.type`, `op: en`, the list of action types that have a tool in `packages/tools`; `si` → `ejecutor`/`ejecutar`, `no` → `ejecutor`/`nota_manual` (a `task` naming the manual step) | an action the policy prescribes with no tool, such as a phone call, still reaches a person |
| "Administrador completa o confirma la acción manual" | no state: the person's confirmation is a `result` event on the `bitácora` | the brief's lifecycle ends at `ejecutada`, and the `task` draft is the execution |
| "Cierre": record and update the state | stage `cerrar`, owned by `apps/api` | unchanged |

One node the diagram does not draw enters with it: **`ejecutar.vigente`**, before every `Ejecutor`
leaf, reads the KPI that justified the approved action on the simulated day of the execution, with
the same `umbral`. `si` (it still breaks) → the leaf; `no` → `fin.ya_no_aplica`, and the alert
records that the condition no longer holds. It is the point where `ejecutar` consults the kernel
(spec 1), and it is code, so `Ejecutor` keeps no discretion. Its `fundamento` is `iso9001.10.2.1.c`,
an action that addresses the nonconformity, which a resolved one no longer has.

## The validator

Code in `packages/agents`, run at startup and as a test. It refuses a tree where:

- a node fails the schema above, or a predicate fails the atomicity test;
- a node lacks its `fundamento`, its `si` or its `no`, or its `fundamento` is absent from
  `fundamentos.yaml`;
- a path reaches an `Ejecutor` leaf without passing the gate `aprobar.decision` and the node
  `ejecutar.vigente`;
- the graph has a cycle other than the two capped returns, `proponer` → `explicar` and
  `aprobar.recargar` → `proponer`;
- a path from the root reaches no `fin`;
- a `lee` names a KPI column the kernel does not build (spec 4), or a state field the alert's state
  does not declare;
- an `umbral` names a metric absent from `metricas.yaml` and from the client's approved KPIs (spec 6);
- a leaf's `skill` does not exist, or its `decision` is outside its agent's list;
- an L0 or L1 node differs from the base in `packages/agents/arbol/` (spec 3).

It replaces the coverage command of `packages/agents/AGENTS.md`: a metric with no L3 branch, or an
L3 leaf whose skill is missing, is a refusal instead of a printed gap.

## The walkthrough: a customer who paid in 30 days is 6 days late

1. `detectar`: no node fires. `saldo_vencido` fires above 15 days (`metricas.yaml`) and
   `dias_pago_prom` above a 50% rise; a 6-day delay on a 30-day habit crosses neither. **The tree
   has no node that sees the case**, and `FIN-POL-004 §4` prescribes a reminder from day 1. This is
   the `kpi_gap` spec 6 is built around, and the walkthrough resumes there once the KPI exists.
2. Once the administrator approves that KPI, `Vigía` self-expands `detectar` with the node
   `detectar.cartera.retraso_habito` (spec 3); on the next simulated day it fires, and
   `vigia`/`titular` writes the title.
3. `explicar`: `analista`/`explicar` crosses payments and behaviour; the "meta de $1.000 en 6
   meses" of the diagram has no source in the data, so it joins the table of what the data cannot
   answer in `packages/agents/AGENTS.md`.
4. `proponer`: `estratega`/`proponer` takes the rows of `acciones.md` for the metric; a reminder
   email is the action `FIN-POL-004 §4` prescribes for 1 to 15 days.
5. `aprobar`: the person approves, edits, rejects, or requests changes once.
6. `ejecutar.vigente`: the invoice is still past due, so the walk goes on;
   `ejecutar.automatizable`: an email draft has a tool, so `ejecutor`/`ejecutar`.
7. `cerrar`: `apps/api` records and moves the alert to `ejecutada`.

## Pages this spec changes

| Page | Change |
|---|---|
| `packages/agents/AGENTS.md`, "The domain of each agent" | becomes "What a leaf may use": per agent, its input, tools, output, ceiling and "never". The sentence "**Each agent answers one question, and no agent answers another's.**" is kept; the routing sentences inside each agent's subsection move to the tree |
| `packages/agents/AGENTS.md`, "The orchestrator's graph" | "Nodes and edges" is replaced by "The decision tree": where the base and the registry live, the node schema, the levels, the validator, `ejecutar.vigente`, and the sentence "The tree compiles to the LangGraph graph; an invalid base stops the start." The state, order, cost and failure subsections stay |
| `packages/agents/AGENTS.md`, "Coverage" | the coverage command is replaced by the validator's test command |
| `packages/agents/AGENTS.md`, "The universe" | a row: the goals of a customer or of the company (the diagram's "meta de $1.000 en 6 meses") — no table records them |
| `packages/agents/skills/AGENTS.md` | the sentence "any other file is loaded only when the alert's metric names it" becomes "any other file is loaded only when the leaf the walk reaches names it" |
| `apps/api/AGENTS.md` | the decision check gains `request_changes` (a reason is required, and it is refused on an alert that already had one); the lifecycle gains no state, because `request_changes` keeps the alert in `propuesta` |
| `apps/web/src/api/types.ts` (draft contract) | `Decision` gains `request_changes`; the alert detail shows "Solicitar cambios" beside approve, edit and reject |
| `evals/AGENTS.md` | `ORQ-` cases: a tree with a missing `no` (refused at startup), a `request_changes` (one re-proposal, a second refused), an action type with no tool (one `task`), an approved action whose KPI no longer breaks on the day of execution (`fin.ya_no_aplica`, `Ejecutor` not called), a path to `Ejecutor` without `aprobar` (refused), the walkthrough above |

## Acceptance

- Every row of today's "Nodes and edges" table maps to a node or a leaf, or to a setting of the
  interpreter with its reason, and the plan of this spec carries that mapping as a checklist.
- The validator refuses one planted violation per rule in its list.
- The `ORQ-` cases of `evals/AGENTS.md` pass on the compiled graph.
