# packages/agents/skills: what each agent is told

A skill is a Markdown file the orchestrator puts in front of a model. Skills are grouped by agent,
one directory each, and an agent is given only its own directory: `vigia/`, `analista/`,
`estratega/`, `ejecutor/`, and `orquestador/` for the one step of the orchestrator that calls a
model. Within it, `contrato.md` is always loaded; any other file is loaded only when the alert's
metric names it. What each agent may and may not do is [`../AGENTS.md`](../AGENTS.md); a skill
turns that page into orders and never widens it.

## Decisions

- **A skill holds no figure from a policy.** It names the view and column that holds the figure
  (`tope_descuento_pct`, `margen_minimo_pct`), the `metricas.yaml` entry, or the policy code and
  section. The figure stays in one place, and a skill cannot state a threshold the data does not.
- **A skill is written in English, and it orders every text meant for a person in Spanish**,
  because the tree's documentation is English and the person who reads an alert reads Spanish.
  Domain words stay in Spanish, in backticks, as the data names them.
- **A window in a hypothesis query is a method, not a business rule.** The weeks, days and shares
  an `analista/` file uses to test a hypothesis decide only which query runs; they never fire an
  alert and are never presented as a policy. A business threshold lives in `metricas.yaml` alone.
- **A skill is sized for a 4 to 8 billion parameter model**: the contract plus one metric file fit
  on one screen, with at most two examples.
- **Examples come only from generated datasets**, never from the official one, marked `EXAMPLE`,
  with the input, the queries and the complete output JSON. They are added from runs on datasets
  of [`../../../data/generator/`](../../../data/generator/) once the agent runs; the official answer
  key is never written here, for the reason [`../../../evals/AGENTS.md`](../../../evals/AGENTS.md) gives.

## How a skill is written

1. **One rule, one sentence, one verb in the imperative.** These words are not used: "consider",
   "may", "might", "could", "usually", "generally", "if possible", "etc.", "and/or".
2. **Every condition has its other branch.** "If A, do X. Otherwise, do Y." No condition is left
   without its "otherwise".
3. **A list is closed and says so**: "The only permitted actions are: …".
4. **A controlled vocabulary.** Every term is a view, a column, an output field or a policy code,
   spelled as the data spells it, in backticks. A thing has one name; no synonyms.
5. **A decision is a table** of condition and result, not a paragraph.
6. **Every skill says what its agent does not do, and which agent does it.**
7. **Every query names its view and its filter on the simulated day**, written `:dia`. A query on a
   whole-year view filters by the column the clock section of
   [`../../../data/AGENTS.md`](../../../data/AGENTS.md) names.
8. **A metric file has at least one path to `no_evidence`**, written as the result that refutes
   every hypothesis.
