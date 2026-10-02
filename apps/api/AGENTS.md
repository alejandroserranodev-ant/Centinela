# apps/api: the API, the clock and the log

This level is the only door into Centinela: the web, the jury and any script reach the agents
through it. It holds no code yet; this page states the decisions the code is written against. The
endpoints it must serve are [`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its
minimal API section.

## Decisions

- **Python, FastAPI and Pydantic**, REST plus SSE streaming for the chat and for agent progress.
- **The API owns the simulated clock.** Advancing it moves the simulated day that replaces
  `fecha_corte()` (see [`../../data/AGENTS.md`](../../data/AGENTS.md), its clock section).
- **The API owns the alert lifecycle and persists it**: `nueva` → `en análisis` → `propuesta` →
  `aprobada` or `rechazada` → `ejecutada`. A transition the lifecycle does not list is refused.
- **The API owns the `bitácora`**, which is append-only: alert, evidence, proposal, decision,
  action and result, each with who and when. Nothing updates or deletes a row of it.
- **Roles decide who may approve.** Full enterprise authentication is out of scope; roles are not.

## Rules of this level

- **No decision, no action.** The API never resumes an alert past the approval interrupt without a
  recorded decision from a role allowed to make it. *No gate holds this.*
- **The API's state lives in its own schema**: alerts, decisions and the log, never in the
  dataset's `centinela` schema.
- **An alert carries its cost**: tokens and model calls are recorded per alert.
- **Timeouts and retries are explicit**, and "not enough evidence" is a valid response, not an error.
