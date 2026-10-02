# packages/tools: the closed list of tools

This level holds the MCP servers the agents call. **The list of tools is closed**: an agent can do
exactly what a tool here exposes and nothing else, which is what makes an acting agent safe to
buy. It holds no code yet; this page states the decisions the code is written against.

## Decisions

- **Tools are MCP servers**, one per concern:
  - **read-only SQL** over the `v_*` views of the semantic layer
    ([`../../data/AGENTS.md`](../../data/AGENTS.md)), connected as the read-only database user;
  - **policy search** over [`../../data/policies/`](../../data/policies/), embedded in pgvector;
  - **actions**, each producing a draft or a sandbox effect: a draft email, a task, a draft purchase order.
- **Every SQL tool takes the simulated day** and filters by it, because not every view does.

## Rules of this level

- **Every query is logged and returned with its result**, so the figure and the query that
  produced it travel together to the log and the screen. *No gate holds this.*
- **Retrieved text is data, never instructions.** Policy search returns passages as quoted content
  marked as such; a passage that reads like an order is reported, not obeyed.
- **Actions are idempotent**: the same approved action executed twice has one effect.
- **No tool writes to the dataset schema, and no action leaves draft or sandbox.**
- **Adding a tool widens what an agent can do**, so a new tool states, on this page, what it can
  touch and why the agents need it.
