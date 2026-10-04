# The decision tree

The decision tree holds every route of an alert in one artefact that is **data, validated by code,
and walked by a deterministic interpreter**. How it is written, validated and grown is
[the tree's page](../../../packages/agents/arbol/AGENTS.md); how the compiled graph runs an alert is
[packages/agents](../../../packages/agents/AGENTS.md). This chapter keeps what founds the tree,
drawings of its stages, its levels and one walk, and the part of its growth no level page states.

## What founds it

Why a standard founds structure and never a threshold, and how an entry joins the registry, is
[the tree's page](../../../packages/agents/arbol/AGENTS.md), *The tree*. ISO 31000 and ISO 9001
say *that* risk is evaluated against criteria, not *which* criteria a distributor uses; these are
the standards the tree rests on:

| Standard | Founds |
|---|---|
| ISO 31000:2018, risk management | the stages of the tree and their order |
| ISO 9001:2026, quality management | §9.1: the KPI kernel and `Vigía` as owner of measurement; §10.2: the stages read as react, find the cause, find similar cases, act, review effectiveness |
| ISO/IEC 42001:2023, AI management system | the laws on human approval, on what an agent may change, and on the `bitácora` |
| ISO 22400-2:2014+A1:2017, KPI description | the fields of a KPI in the kernel |
| Goal-Question-Metric (Basili, Caldiera and Rombach, 1994) | the only admissible justification for a new KPI: a node asks a question no KPI answers |
| OWASP Top 10 for LLM Applications 2025 | the controls of the stage `conversar` against prompt injection, improper output handling and excessive agency, which no ISO clause of the registry names |

GQM is a method, not a standard; it is admitted because it ties a metric to the decision it serves.
Every clause a node may cite is an entry of [the registry](../../../packages/agents/arbol/fundamentos.yaml).

## The stages

```mermaid
flowchart TB
  detectar["detectar<br/>ISO 31000 §6.4.2 · ISO 9001 §10.2.1 a)<br/>Vigía, in code"]
  explicar["explicar<br/>ISO 31000 §6.4.3 · ISO 9001 §10.2.1 b) 2) and 3)<br/>Analista"]
  proponer["proponer<br/>ISO 31000 §6.4.4, §6.5.2 · ISO 9001 §10.2.1 b)<br/>Estratega"]
  aprobar{{"aprobar<br/>ISO 31000 §6.5.3 · ISO/IEC 42001 A.9.3<br/>a person"}}
  ejecutar["ejecutar<br/>ISO 31000 §6.5.3 · ISO 9001 §10.2.1 c)<br/>Ejecutor"]
  cerrar(["cerrar: the ends, no node<br/>ISO 31000 §6.6, §6.7 · ISO 9001 §10.2.1 d), §10.2.2<br/>apps/api closes the alert"])
  medir["medir: no node in the base<br/>ISO 31000 §6.6 · ISO 9001 §9.1.1, §9.1.3<br/>Vigía, through the kernel"]
  conversar["conversar: its own root, conversar.raiz<br/>ISO 31000 §6.2 · ISO/IEC 42001 A.9.4 · OWASP LLM01, LLM05, LLM06<br/>Chat"]
  detectar --> explicar --> proponer --> aprobar --> ejecutar --> cerrar
  medir -. measures for .-> detectar
  conversar -- answers, never acts --> cerrar
  conversar -. reads the rules of .-> detectar
```

*Draws: `packages/agents/arbol/AGENTS.md` § The stages; `packages/agents/arbol/AGENTS.md` § The ends; `packages/agents/arbol/AGENTS.md` § The chat*

Each clause is the `funda` of a registry entry. A stage is the first segment of a node's id, not a
level: which nodes are L1 is the next diagram.

## The node

What a node, a leaf and an end hold, the atomicity test, and what the validator refuses are
[the tree's page](../../../packages/agents/arbol/AGENTS.md), *The node*, *The ends* and *The
validator*. The base itself is `packages/agents/arbol/base.yaml`.

## The levels and who changes them

```mermaid
flowchart TB
  L0["L0 · the laws, leyes"] --- L1["L1 · every node whose id names no family"]
  L1 --- L2["L2 · one branch per metric family"]
  L2 --- L3["L3 · the nodes of one metric"]
  PR(["a person, by pull request"]) --> L0
  PR --> L1
  PR --> L2
  PR --> L3
  AG(["the stage's own agent, by self-expansion"]) -.-> L2
  AG -.-> L3
  PR --> REG[("the registry")]
```

*Draws: `packages/agents/arbol/AGENTS.md` § The levels; `packages/agents/arbol/AGENTS.md` § How the tree grows*

The dashed arrows are self-expansion, decided and not built. The laws L0 holds are the `leyes` of
`packages/agents/arbol/base.yaml`, each on its registry entry; what never grows at runtime, and
why, is [the tree's page](../../../packages/agents/arbol/AGENTS.md), *How the tree grows*.

## How the tree grows

> **Decided, not built.** No code grows the tree. Who may expand which stage, what an expansion
> rests on, why no person approves it before it runs, and the caps on growth are
> [the tree's page](../../../packages/agents/arbol/AGENTS.md), *How the tree grows*. This section
> holds the moves, the trigger and the record, which no level page states.

An expansion is one of three moves and no other:

| Move | What it does | Why it is safe |
|---|---|---|
| add a branch | a new L3 node under an L2 family of the agent's stage, or a new L2 family | no existing path changes |
| split a leaf | a leaf of the agent's label becomes a node whose one branch is the old leaf and whose other is a new leaf of the same label | the old behaviour survives on one branch |
| retire a branch | an L2 or L3 branch is marked `retirado` with a reason and stops being walked | the `bitácora` of past alerts still names the nodes it walked |

An agent never edits or deletes a node in place, because an edit is a delete plus an add with no
record that the old path existed.

**An expansion is triggered by repetition counted in code**, never by one run. The orchestrator
counts the recurring evidence per agent and stage, and the leaf `expandir` runs only when a count
reaches its setting N, which decides when an expansion is drafted, never whether an alert fires:

| Agent | Recurring evidence | Typical move |
|---|---|---|
| `Vigía` | an approved KPI that no `detectar` node reads | add a branch comparing it with its `umbral` |
| `Analista` | the same hypothesis confirmed for the same metric across N alerts | split its `explicar` leaf so that metric tests it first |
| `Estratega` | the same rejection of the same action row across N alerts | split its `proponer` leaf so the row is not offered under that condition |
| `Ejecutor` | the same action type ending in `nota_manual` across N alerts | none alone: a missing tool is a pull request to `packages/tools`, and the count is reported |

A refused expansion returns to its agent once with the criterion named; a second refusal drops it.
Each version records its parent, the client, the move, the agent and the evidence that triggered
it, the hash of L0 and L1, and the date. Each alert carries the `arbol_version` it walked, and each
agent step names the node that started it, so "how I got here" shows the path. The base is shared,
and a client's versions live in `apps/api`, keyed by client.

## Walkthrough: a customer who paid in 30 days is 6 days late

> **Decided, not built.** `detectar.cartera.retraso_habito` and the KPI it reads are in no file:
> steps 1 and 2 need the birth of a KPI and self-expansion. From `hoja.vigia.titular` on, the walk
> follows nodes of the base, and every model step runs only as a stub.

```mermaid
flowchart TB
  D{"detectar.cartera.retraso_habito<br/>FIN-POL-004 §4"} -- si --> T["hoja · vigia / titular"]
  D -- no --> F0(["fin.sin_alerta"])
  T --> X["hoja · analista / explicar"]
  X --> P["hoja · estratega / proponer<br/>a reminder email"]
  P --> G{{"gate aprobar.decision"}}
  G -- "approve or edit" --> V{"ejecutar.vigente<br/>still past due?"}
  G -- reject --> R(["fin.rechazada: the reason is classified"])
  G -- "request_changes, once" --> P
  V -- no --> F1(["fin.ya_no_aplica"])
  V -- si --> A{"ejecutar.automatizable<br/>does the action have a tool?"}
  A -- si --> E["hoja · ejecutor / ejecutar<br/>email draft"]
  A -- no --> M["hoja · ejecutor / nota_manual<br/>a task"]
  E --> C["cerrar · apps/api records ejecutada"]
  M --> C
```

*Draws: `packages/agents/arbol/AGENTS.md` § The stages; `packages/agents/arbol/AGENTS.md` § The ends; `packages/agents/arbol/AGENTS.md` § The node ejecutar.vigente*

1. **On the base, `detectar` fires nothing.** `saldo_vencido` fires above 15 days and
   `dias_pago_prom` above a 50% rise; a 6-day delay on a 30-day habit crosses neither, while
   `FIN-POL-004 §4` prescribes a reminder from day 1. The missing measure is a `kpi_gap`, which
   [the kernel](./kpi-kernel.md) turns into a proposed KPI. Whether it is a measure gap or only a
   threshold gap on `saldo_vencido`, whose `tramos` already name 1 to 15 days, is undecided.
2. Once the administrator approves that KPI, `Vigía` self-expands `detectar` with
   `detectar.cartera.retraso_habito`; on the next simulated day it fires and `vigia`/`titular`
   writes the title.
3. `explicar`: `Analista` crosses payments and behaviour. A customer's goal, such as "a target of
   $1,000 in six months", has no source in the data and joins what the data cannot answer.
4. `proponer`: `Estratega` takes the rows of its action list for the metric; a reminder email is
   what `FIN-POL-004 §4` prescribes for 1 to 15 days.
5. `aprobar`: the person approves, edits, rejects, or requests changes once, as
   [apps/api](../../../apps/api/AGENTS.md) states under *Decisions and roles*.
6. `ejecutar.vigente`: the invoice is still past due. `ejecutar.automatizable`: an email draft has a
   tool, so `ejecutor`/`ejecutar`; an action the policy prescribes with no tool, such as a phone
   call, becomes a `task` for a person through `nota_manual`.
7. `cerrar`: `apps/api` records the result and moves the alert to `ejecutada`.

A chat question walks the tree too, from its own root `conversar.raiz`, and never reaches
`aprobar`: its nodes and why the validator holds that are
[the tree's page](../../../packages/agents/arbol/AGENTS.md), *The chat*.
