# packages/agents/skills: what each agent is told

A skill is a Markdown file of orders for a model. Skills are grouped by agent, one directory each:
`vigia/`, `analista/`, `estratega/`, `ejecutor/`, `chat/`, and `orquestador/` for the one step of
the orchestrator that calls a model. What each agent may and may not do is
[`../AGENTS.md`](../AGENTS.md); a skill turns that page into orders and never widens it. Code reads
three things here: a leaf's `skill` must name a file under this directory,
`estratega/acciones.md` is parsed, and each leaf of `../centinela_agents/agents/` loads its
agent's contract as its model's system prompt, `../centinela_agents/skills.py:skill(agent, names)`;
`Ejecutor` also loads the orders of its one leaf, `ejecutor/plantillas.md` for an email body, never
both leaves' orders, because a small model follows the other leaf's format; `ejecutor/nota_manual.md`
holds a manual note's, which no running leaf asks a model for. The leaf's user prompt carries only the alert and
the facts its code read; a leaf of `Chat` adds the person's question, marked as untrusted data, and
both of its steps load `chat/contrato.md`.

## Decisions

- **A leaf's `skill` names the file its step starts from**: the contract of its agent, or, for
  `revision_manual`, the table of owners in `estratega/acciones.md`. It selects a file, never the
  agent's directory, and the validator refuses a leaf whose `skill` is no file here.
- **`estratega/acciones.md` is parsed by code, so its two tables keep their shape.**
  `centinela_agents/validator.py:coverage_problems(tree, grounds)` reads the text before its first
  `## ` heading and needs a row starting with each metric of `data/metricas.yaml`, in backticks,
  in the first column. `centinela_agents/graph.py:manual_owners(acciones)` reads the section under
  the heading `centinela_agents/graph.py:MANUAL_REVIEW_OWNERS`, the first two columns of each row
  after its separator, each in backticks, as metric and owner. `tests/test_orq.py` holds that every metric has its
  owner, and `tests/test_validator.py` that a metric with no row is refused.
- **A skill holds no figure from a policy.** It names the view and column that holds the figure
  (`tope_descuento_pct`, `margen_minimo_pct`), the `data/metricas.yaml` entry, or the policy code
  and section. The figure stays in one place, and a skill cannot state a threshold the data does
  not.
- **A skill is written in English, and it orders every text meant for a person in Spanish**,
  because the tree's documentation is English and the person who reads an alert reads Spanish.
  Domain words stay in Spanish, in backticks, as the data names them.
- **A window in a hypothesis query is a method, not a business rule.** The weeks, days and shares
  an `analista/` file uses to test a hypothesis decide only which query runs; they never fire an
  alert and are never presented as a policy. A business threshold lives in `data/metricas.yaml`
  alone.
- **A skill is sized for a 4 to 8 billion parameter model**: the contract plus one metric file fit
  on one screen, with at most two examples.
- **Examples come only from generated datasets**, never from the official one, marked `EXAMPLE`,
  with the input, the queries and the complete output JSON. They come from runs on datasets of
  [`../../../data/generator/`](../../../data/generator/); the official answer key is never written
  here, for the reason [`../../../evals/AGENTS.md`](../../../evals/AGENTS.md) gives.

> **Decided, not built.** The metric files: `<metric>.md` is to be loaded for an alert of that
> metric, once a leaf can run the view queries its hypotheses
> name. Of the table in `estratega/acciones.md`, only the rows of the alert's metric reach the
> model, as refs in the user prompt, because the token cost of each alert is recorded and judged. A pending spec adds a file per decision for
> `expandir` and `proponer_kpi`, loaded only when the walk reaches that decision's leaf.

## How a skill is written

1. **One rule, one sentence, one verb in the imperative.** These words are not used: "consider",
   "may", "might", "could", "usually", "generally", "if possible", "etc.", "and/or".
2. **Every condition has its other branch.** "If A, do X. Otherwise, do Y." No condition is left
   without its "otherwise".
3. **A list is closed and says so**: "The only permitted actions are: …".
4. **A controlled vocabulary.** Every term is a view, a column, a field of the alert's state, an
   output field or a policy code, spelled as the data spells it, in backticks. A thing has one
   name; no synonyms.
5. **A decision is a table** of condition and result, not a paragraph.
6. **Every skill says what its agent does not do, and which agent does it.**
7. **Every query names its view and its filter on the simulated day**, written `:dia`. A query on a
   whole-year view filters by the column the clock section of
   [`../../../data/AGENTS.md`](../../../data/AGENTS.md) names.
8. **A metric file has at least one path to `no_evidence`**, written as the result that refutes
   every hypothesis.

## Adding a skill

1. **A metric file**, `analista/<metric>.md`, for every metric of `data/metricas.yaml`: its entity,
   spelled as the KPI's `kernel.agrupar` names it; when its symptom starts; a table of hypotheses
   with the query, the result that holds and the one that refutes; the order they are tested in;
   when to set `same_cause_as`; and its path to `no_evidence`. Then the metric's rows in both
   tables of `estratega/acciones.md`, each row's first column the metric in backticks.
2. **A contract**, `<agent>/contrato.md`, for a new decision of an agent: its input as the fields of
   the alert's state the leaf receives, its tools, its output, its procedure as tables, and what
   it does not do. The leaf that takes the decision names it in `skill`, as
   [`../arbol/AGENTS.md`](../arbol/AGENTS.md) orders.
3. **Any other file** is loaded with its agent's directory, so it costs tokens on every alert; it
   earns its place only when no contract can hold it.
4. Run `uv run pytest` from `packages/agents`: the validator checks every `skill` and the coverage
   of `estratega/acciones.md`.
