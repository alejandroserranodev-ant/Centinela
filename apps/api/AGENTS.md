# apps/api: the API, the clock and the log

This level is the only door into Centinela: the web, the jury and any script reach the agents
through it. It holds the skeleton the endpoints are built on: FastAPI, the API's own schema, the
alert lifecycle and the `bitácora`, not yet wired to `packages/agents` or `packages/tools`. This
page states the decisions the code is written against. The endpoints it must serve are
[`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its minimal API section.

## Decisions

- **Python, FastAPI and Pydantic**, REST plus SSE streaming for the chat and for agent progress.
- **The API owns the simulated clock.** Advancing it moves the simulated day that replaces
  `fecha_corte()` (see [`../../data/AGENTS.md`](../../data/AGENTS.md), its clock section).
- **The API owns the alert lifecycle: it validates every transition and persists it**, and
  refuses one the lifecycle does not list. The orchestrator proposes the transitions an agent
  causes, because it is the only part that sees an agent finish; the API proposes the ones a
  person causes. The record is the API's, because it is the only part with storage and the only
  door. How the orchestrator reaches each proposal is
  [`../../packages/agents/AGENTS.md`](../../packages/agents/AGENTS.md), its graph section.

  | Transition | Proposed by |
  |---|---|
  | → `nueva` | the orchestrator, when `Vigía` detects |
  | `nueva` → `en análisis` | the orchestrator, when the title is written |
  | `en análisis` → `propuesta` | the orchestrator, when `Estratega` proposes |
  | `en análisis` → `unida` | the orchestrator, when it merges the alert into one analysed before it |
  | `nueva` → `unida` | the orchestrator, when an alert of the same day, analysed first because its pesos at risk are larger, names this one as the same cause |
  | `propuesta` → `aprobada` or `rechazada` | the API, from a person's decision |
  | `aprobada` → `ejecutada` | the orchestrator, when `Ejecutor` returns its result |

- **`unida` is a state the brief's lifecycle does not have.** An alert whose cause `Analista` finds
  already explains another alert ends there, pointing to the alert that remains, because the brief
  asks that one cause raise one alert and its lifecycle has no end for the second. `rechazada`
  would claim a decision no person made, so `unida` is final and never counts as decided.
- **A merge keeps one alert in view and loses nothing.** The API accepts a transition to `unida`
  only while its target is in `nueva`, `en análisis` or `propuesta`, checked in the transaction
  that records it, so every alert of one cause points to the one that remains and none points to a
  merged alert. The inbox lists only the alert that remains, and its detail carries, beside its
  own, the detection and evidence of each alert in its `merged_alerts`. Its pesos at risk stay its
  own, because two detections of one cause would count the same pesos twice.
- **One day run at a time.** A call to `/simulacion/avanzar` while a day run is in course is
  refused with 409, because the second run would detect against earlier alerts the first has not
  recorded yet, and one cause would raise two alerts.
- **The API hands each run what the orchestrator cannot read**: the metric, entity, severity and
  state of every earlier alert, and the rejection reasons kept for the alert's metric. It keeps
  each reason with the target the orchestrator classified it to, the metric and the entity.
- **The API checks a decision before it resumes an alert**: the role may make it, a rejection
  carries a reason, an edit keeps the keys of the action's `parameters`, adding none and dropping
  none, because `Ejecutor` passes them unchanged, and a `request_changes` carries a reason and is
  refused on an alert that already had one, because the return to `Estratega` is capped at one.
- **`request_changes` adds no state to the lifecycle.** The alert stays `propuesta` while
  `Estratega` proposes again, and its reason joins the rejection reasons `Estratega` reads, because
  a person asking for another proposal has neither approved nor rejected the alert.
- **The API stores the graph's checkpoints in its own schema** and injects the checkpointer into
  the graph, because no agent opens a database connection.
- **The API owns the `bitácora`**, which is append-only: alert, evidence, proposal, decision,
  action and result, each with who and when. Nothing updates or deletes a row of it.
- **Roles decide who may approve.** Full enterprise authentication is out of scope; roles are not.

## Rules of this level

- **No decision, no action.** The API never resumes an alert past the approval interrupt without a
  recorded decision from a role allowed to make it. *No gate holds this.*
- **The API's state lives in its own schema**: alerts, decisions and the log, never in the
  dataset's `centinela` schema.
- **An alert carries its cost**: the API persists the tokens and model calls the orchestrator
  counts per alert, and per chat answer.
- **Timeouts and retries are explicit**, as the orchestrator's graph states them, and "not enough
  evidence" is a valid response, not an error.
