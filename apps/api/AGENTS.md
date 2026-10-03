# apps/api: the API, the clock and the log

This level is the only door into Centinela: the web, the jury and any script reach the agents
through it. No code exists here; every section below is a decision the code is written against.
Until it lands, `apps/web` runs on a simulated API that mirrors the endpoint table below
([`../web/AGENTS.md`](../web/AGENTS.md)).

> **Decided, not built.** Everything on this page.

## The planned layout

- **A uv project in this directory**, with its pyproject.toml and uv.lock beside this page, as
  `packages/agents` and `packages/tools` have, so its commands run with `uv run` and are named
  here. Its import package sits beside the manifest.
- **Python, FastAPI and Pydantic**, REST plus SSE streaming for the chat and for agent progress.
- **The Pydantic models live in that package and are the contract's source.**
  `apps/web/src/api/types.ts` follows them.
- **The API's state lives in its own PostgreSQL schema**: alerts, decisions, the `bitácora`, the
  graph's checkpoints and the KPI catalogue, never the dataset's `centinela` schema.
- **The checkpointer writes to that schema**, and the API injects it into the graph, because no
  agent opens a database connection.
- **Undecided:** the schema's name, how its tables are created and migrated, and which LangGraph
  saver writes the checkpoints. Whoever writes the first code here decides them and writes them on
  this page. Whether the agents run in this process or as a service is an open question of the
  root [`../../AGENTS.md`](../../AGENTS.md).

## Endpoints

The brief's minimal API is [`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its
minimal API section; its paths stay as the brief writes them. The other rows are what the screens
need beyond it, consumed through `apps/web/src/api/client.ts`. A path marked undecided is chosen
with the code, in Spanish like the brief's.

| Method | Path | Serves | Refuses | Web function |
|---|---|---|---|---|
| POST | `/simulacion/avanzar?dias=1` | advances the clock and runs the day; streams `step`, `alert` and `end` events by SSE | 409 while a day run is in course | `advanceDay` |
| GET | `/alertas?estado=propuesta` | the inbox, ordered by pesos at risk; merged alerts are not listed | | `listAlerts` |
| GET | `/alertas/{id}` | cause, evidence, actions and the alerts merged into it | 404 for an unknown alert | `getAlert` |
| POST | `/alertas/{id}/decision` | `approve`, `edit`, `reject` or `request_changes` | 404; 409 when the alert is no longer `propuesta`; 422 for each check of a decision below | `decide` |
| POST | `/chat` | a question, answered by SSE `step`, `chunk` and `end` events | | `chat` |
| GET | `/bitacora` | the log, filtered by alert and by event type | | `listBitacora` |
| GET | undecided | the simulated day and the person signed in, with a role | | `getSimulationState` |
| GET | undecided | the inbox totals: pesos at risk today, decisions pending, recoverable per month | | `getInboxSummary` |
| GET | undecided | the watched KPIs, thresholds, owners and autonomy per action type | | `getSettings` |
| undecided | undecided | saves the settings whole | 422 when any action type's autonomy is `execute` | `saveSettings` |
| GET | undecided | one query by id, for "how I got here" | 404 for an unknown query | `getQuery` |

**The KPI catalogue's endpoints**, which list the base and approved KPIs and let the administrator
decide a proposed KPI or retire one, are decided by the pending work on a new KPI's lifecycle, and
become rows here when it is planned.

### Adding an endpoint

1. Add its row to the table above first: method, path, what it serves, what it refuses, and the
   web function that consumes it.
2. Write its Pydantic model in the package; the web's draft type follows it.
3. Once code lands, the manifest of this directory has this page beside it, which `check:agents`
   holds, and this page names its commands.

## The clock

**The API owns the simulated clock.** Advancing it moves the simulated day that replaces
`fecha_corte()` (see [`../../data/AGENTS.md`](../../data/AGENTS.md), its clock section).

**One day run at a time.** A call to `/simulacion/avanzar` while a day run is in course is refused
with 409, because the second run would detect against earlier alerts the first has not
recorded, and one cause would raise two alerts.

**The API hands each run what the orchestrator cannot read**: the metric, entity, severity and
state of every earlier alert, and the rejection reasons kept for the alert's metric. It keeps each
reason with the target the orchestrator classified it to, the metric and the entity.

## The alert lifecycle

**The API validates every transition and persists it**, and refuses one the lifecycle does not
list. The orchestrator proposes the transitions an agent causes, because it is the only part that
sees an agent finish; the API proposes the ones a person causes. The record is the API's, because
it is the only part with storage and the only door. How the orchestrator reaches each proposal is
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

## Decisions and roles

**The API checks a decision before it resumes an alert**, and answers 422 when a check fails:

- the person's role may decide the alert;
- a rejection carries a reason;
- an approval or an edit names one of the alert's proposed actions;
- an edit keeps the keys of the action's `parameters`, adding none and dropping none, because
  `Ejecutor` passes them unchanged;
- a `request_changes` carries a reason, and is refused on an alert that already had one.

**A `request_changes` is capped at one per alert**, because a person who still disagrees after
one new proposal has the decision in hand: an edit says what to change and a rejection says why,
and both close the alert. The alert stays `propuesta` while `Estratega` proposes again, and the
reason joins the rejection reasons `Estratega` reads, because a person asking for another proposal
has neither approved nor rejected the alert.

**Roles decide who may decide.** The person who decides an alert holds the role the settings name
as the owner of its metric, among the roles the policies name, such as `Gerente comercial` or
`Jefe de cartera`. The `administrador` role decides the KPI catalogue. Every row of the `bitácora`
a person causes carries their name and role. Full enterprise authentication is out of scope;
roles are not.

**"Ejecuta" is refused for every action type**, with 422 on saving the settings, because the
challenge keeps every action at `Propone` ([`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md),
its responsible AI section).

## The inbox totals

**The API computes the inbox totals**: pesos at risk today and recoverable per month, each a sum
over the alerts in `propuesta`, and the count of decisions pending. They are sums over alerts
rather than a `v_*` view, so the API sends each as a figure whose query reads its own alerts
table, and the screen computes none.

## The `bitácora`

**The API owns the `bitácora`**, which is append-only: alert, evidence, proposal, decision,
action and result, each with who and when. Nothing updates or deletes a row of it.

## Rules of this level

- **No decision, no action.** The API never resumes an alert past the approval interrupt without a
  recorded decision from a role allowed to make it. *No gate holds this.*
- **The API's state lives in its own schema**, never in the dataset's `centinela` schema.
- **An alert carries its cost**: the API persists the tokens and model calls the orchestrator
  counts per alert, and per chat answer.
- **Timeouts and retries are explicit**, as the orchestrator's graph states them, and "not enough
  evidence" is a valid response, not an error.
