# Open work

This page indexes what Centinela still has to build: one line per item, each linking the section
that owns the decision or the debt. It holds no decision and no debt of its own; when an item is
built, its owner drops the `Decided, not built` box and its line here goes. It sits at the root,
outside any level, because the team keeps the file structure; the levels' pages remain the source.

Re-derive the boxes this page indexes with
`grep -rn "Decided, not built" --include=AGENTS.md apps packages data evals`.

## The day run, from detection to the inbox

- **Detection on the simulated day through the kernel**, instead of the demo rows `apps/api` hands
  the walk: [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#the-agents-run-in-this-process) and
  [`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#the-day-run).
- **One day run at a time, and the earlier alerts and rejection reasons handed to each run**:
  [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#the-clock).
- **Merging an alert into the one that explains it (`unida`)**:
  [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#the-alert-lifecycle).
- **Retries, timeouts and the step that fails**:
  [`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#how-a-step-runs).

## What an agent may use

- **The skills loaded into each model step**, instead of the inline prompts:
  [`packages/agents/skills/AGENTS.md`](./packages/agents/skills/AGENTS.md#decisions).
- **The tools a leaf calls**: SQL over the views, policy search, `calcular_impacto` and the actions,
  owned by [`packages/tools/AGENTS.md`](./packages/tools/AGENTS.md#the-other-tools), and the leaves'
  side in [`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#what-a-leaf-may-use).
- **Masking before a model reads data**:
  [`packages/tools/AGENTS.md`](./packages/tools/AGENTS.md#masking).
- **Idempotent actions**:
  [`packages/tools/AGENTS.md`](./packages/tools/AGENTS.md#actions-and-idempotency).
- **The model the team runs**: [`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#models).

## The person's side

- **Roles by the owner of each metric, `request_changes` and its cap**:
  [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#decisions-and-roles).
- **The inbox totals, the settings and "how I got here"**, which the web answers in the browser
  today: [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#the-inbox-totals) and
  [`apps/api/AGENTS.md`](./apps/api/AGENTS.md#endpoints).
- **The routing of the chat**: [`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#routing).

## Cost, trace and proof

- **Cost and trace per alert**: [`packages/agents/AGENTS.md`](./packages/agents/AGENTS.md#cost-trace-and-log).
- **The evaluation cases and their runner**: [`evals/AGENTS.md`](./evals/AGENTS.md#the-cases-of-each-agent).
- **The tree's growth and the approved-KPI file**:
  [`packages/agents/arbol/AGENTS.md`](./packages/agents/arbol/AGENTS.md#how-the-tree-grows) and
  [`packages/tools/AGENTS.md`](./packages/tools/AGENTS.md#the-approved-kpi-file).

## Debts across levels

The defects that span more than one level are filed in [`DOUBTS.md`](./DOUBTS.md#filed-debts).
