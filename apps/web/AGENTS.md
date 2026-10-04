# apps/web: the decision inbox

This level is Centinela's interface: a **decision inbox, not a dashboard**. Its screens read and
write `apps/api` over HTTP through one fetch client. Running the web against the API and the database is
[`../../CONEXION_WEB_API.md`](../../CONEXION_WEB_API.md). Which screens the challenge asks for
and what each shows is
[`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its screens section.

## Why each file exists

| Path | Why it exists |
|---|---|
| `src/main.tsx` | mounts the app with the Spanish locale strings of Arena's components, the theme and the router, and imports the generated stylesheets |
| `src/App.tsx` | the web's routes, each a screen inside the shell |
| `src/screens/` | one component per screen (`Inbox`, `Bitacora`, `Settings`, `Chat`), and the pieces only one screen renders: the alert's list, detail, proposed actions, "how I got here" and the dialogs that edit, reject or request changes |
| `src/shell/` | what wraps every route: the bar with the simulated day, the navigation, and the agents' current step |
| `src/common/` | the pieces several screens or the shell render: severity, status and confidence badges, a sentence whose figures link to their query, the query dialog, the series chart |
| `src/state/` | `src/state/Simulation.tsx`: the simulated day, the day run in course, the notices, the open query and the open chat, shared by every screen through one provider |
| `src/api/client.ts` | the one module the screens import the API from; it re-exports `src/api/http-client.ts` |
| `src/api/http-client.ts` | the fetch client, one function per endpoint, with the SSE streams read as async iterators |
| `src/api/sse.ts` | `readSse(body)`, which reads a server-sent event stream as `event` and parsed `data` pairs, the name from each event's `event:` line; `src/api/sse.test.ts` tests it with Node's test runner |
| `src/api/config.ts` | the API's base URL, read from `VITE_API_URL`, and the person every decision is sent as |
| `src/api/types.ts` | the contract the client and the screens share, following `apps/api`'s Pydantic models |
| `src/api/fixtures/` | the illustrative data the screens ran on before the fetch client; no module imports it |
| `.env` | the `VITE_API_URL` Vite reads, versioned with the local API's address |
| `src/format.ts` | every number and date as a person reads it: pesos, percentages, points, days and units in `es-CO`, dates in the time zone of Bogotá |
| `src/actionParameters.ts` | the Spanish name of each key of an action's `parameters`, for the proposal, the edit dialog and the `bitácora` |
| `src/app.css` | the layout Arena does not ship, written in Arena's tokens only: the shell's grid, the inbox's two columns, the alert row, the totals, the chat bubbles |
| `index.html` | the page shell; its inline script puts the stored or preferred palette's class on the document before React loads, so the first paint wears the right theme. Its palette list matches `arena.config.json` and the call to `initArenaTheme` in `src/main.tsx` |
| `vite.config.ts` | Vite with the React plugin and nothing else |
| `tsconfig.json` | strict TypeScript over `src/` and the Vite config, with no emit, because Vite builds and `tsc` only checks; it allows `.ts` import paths, because Node runs a test's imports as written |
| `arena.config.json` | Centinela's palettes, light and dark, its fonts, and the style plugin Arena reads |
| `design/centinela/plugin.tokens.json` | the style plugin: Centinela's answer to every role Arena's style kernel asks |
| `design/identity.html` | the approved appearance, each choice with its reason |
| `package.json`, `package-lock.json` | the app's manifest and its pinned dependencies; the lockfile is written by npm ([`../../GENERATED.md`](../../GENERATED.md)) |

## Decisions

- **A Vite + React single-page application, built on Arena React**, where the brief recommends
  Next.js. The backend is Python, so Next.js would add a second server to the stack. The tool
  lives behind a login and nobody outside it has to find it, so server rendering and metadata buy
  nothing. A single-page application is the simplest thing that serves the inbox. React stays on
  18 because it is the version Arena's own suites exercise.
- **Arena is Dravensoft's design system, and Centinela wears its own skin.** The palettes and the
  fonts are in `arena.config.json`. The style plugin is `design/centinela/plugin.tokens.json`,
  which answers every role Arena's kernel asks. It is Arena's `inbox` register at medium density
  rather than compact, because the inbox holds a handful of costly decisions rather than hundreds
  of messages, and it is read on a phone. Components are never styled by hand. Load the
  `arena:design` skill before building or changing a screen. Charts follow the `dataviz` skill.
- **`design/identity.html` is the approved appearance**: palette, faces, character, air and page
  shape, each with its reason. A change to the config or the plugin starts there and is approved
  there. It reads the stylesheet `arena-to-prod` writes, which imports Arena's sheets by package
  name, so it is opened through `npm run dev` at `/design/identity.html`, never from `file://`.
- **The screens import the API from `src/api/client.ts` alone**, which re-exports the fetch
  client, so the client behind it changes without touching a screen. It exports `advanceDay`,
  `listAlerts`, `getAlert`, `decide`, `chat` and `listBitacora` for the brief's minimal API, and
  `getSimulationState`, `getInboxSummary`, `getSettings`, `saveSettings` and `getQuery` for what
  the screens need beyond it. Each endpoint, its route and what it refuses are
  [`../api/AGENTS.md`](../api/AGENTS.md), its endpoint table. A refusal reaches a screen as
  `src/api/http-client.ts:ApiError(status, message)` with the API's status.
- **Some functions answer inside the client**, because the API serves no endpoint for them:
  `getSimulationState` reads the day from `GET /simulacion/dia-actual` and takes the person from
  the client; `getInboxSummary` sums the alerts in `proposed`; `getSettings` returns a constant;
  `saveSettings` refuses `execute` with 422 and stores nothing; `getQuery` refuses every id with
  404, so "how I got here" and the query dialog show their error state.
- **There is no login.** `src/api/config.ts:getDecisionHeaders()` sends every decision as
  `DEFAULT_USER`, a `gerente`, its name percent-encoded in `X-User-Name` because a header is
  ASCII-only.
- **`src/api/types.ts` is the contract the screens read**: `apps/api`'s Pydantic models are the
  source, and these types follow them field for field. Every number travels as a `Figure` with its
  `queryId`, so the type itself asks each figure for its query. Where the types and the API
  disagree is listed under the rules below.
- **The agents' current step is on screen while they work.** `src/shell/CurrentStep.tsx:CurrentStep()`
  renders the `step` events of the day run, which `apps/api` streams by SSE
  ([`../api/AGENTS.md`](../api/AGENTS.md)).
- **Code is written in English; what a person reads stays in Spanish.** Files, components,
  functions, types, props, state keys and our own CSS classes are English. Every text on screen,
  including `aria-label`s, hints and notices, is Spanish, and so is the displayed content of the
  fixtures and of the settings the client returns. The words the data names keep their Spanish in code too: the agents (`vigia`,
  `analista`, `estratega`, `ejecutor`), the metrics (`margen_pct`…), the `v_*` views and the
  `alertas` table, because a translation would make a second name for one thing.
- **The contract is English except its routes.** Field names and values in
  `src/api/types.ts` are English (`status: 'proposed'`, `severity: 'critical'`), so the
  `apps/api` models and the web read one vocabulary of code. The endpoint paths and their query
  string stay as the brief writes them, because the jury calls them by those names; where the
  brief's query string carries a lifecycle value, `src/api/http-client.ts:listAlerts(filter)` sends
  the brief's spelling (`proposed` travels as `estado=propuesta`).
- **The web's own routes are Spanish** (`/alertas/:id`, `/bitacora`, `/configuracion`), because the
  address bar is on screen during the demo and the paths mirror the API and the brief's screen
  names.
- **Fixture files and ids are English** (`src/api/fixtures/alerts.json`, `alert-hogar-margin`,
  `q-hogar-drop`); the line name stays as the data spells it. An id never reaches a manager's
  screen.
- **The fixtures in `src/api/fixtures/` are illustrative**, and no module imports them. They are
  built from the brief's public example (the margin of line `Hogar`, supplier X, $42 M a month) and from entities named as
  examples, never from the dataset, because figures read from `data/csv/` would name the seeded
  scenarios (see the scenarios section of [`../../data/AGENTS.md`](../../data/AGENTS.md)). Each
  figure cites an example query against a real `v_*` view; the queries are not run.
- **The screen computes no figure.** The inbox totals are `Figure`s the API computes
  ([`../api/AGENTS.md`](../api/AGENTS.md#the-inbox-totals)), and their queries read the alerts
  table, which is why `src/api/types.ts:QuerySource` also takes `alertas`. A sum taken on screen
  would be a figure with no query behind it. Until the API serves the totals,
  `src/api/http-client.ts:getInboxSummary()` takes those sums in the browser, under query ids no
  query answers.
- **A notice closes after five seconds, with or without an action**, where Arena's own queue waits
  4.2 s, or 7 s for a notice that carries an action. The demo lasts five minutes, and a stack of
  notices covers the reading column. A danger notice still stays until it is closed, by Arena's
  rule `arenaToastDelay`, which `src/state/Simulation.tsx:useToasts()` applies with the shorter
  interval.
- **Each chart sits in a box that clips sideways**, the `chart` class of `src/app.css`.
  `ArenaLineChart` hides its accessible table in a one-pixel box, but a table lays out to its
  content anyway and would widen the page at phone width. Clipping the inline axis alone keeps the
  tooltip whole.
- **The chat is a non-modal `ArenaSheet`, so it handles focus itself.** The sheet takes no focus
  and traps none, and Escape reaches it only from inside. Opening moves focus to the question
  field, and closing returns it to the control that opened the chat. On a desktop the shell gives
  up the sheet's width at its inline end while the chat is open, so the alert stays readable
  beside the answer. The sheet covers the end of the bar while it is open, because Arena places it
  above fixed navigation.
- **Enter sends a question and Shift + Enter breaks the line.** `ArenaTextarea` exposes no key
  events, so the form around it listens for them. The conversation lasts as long as the app stays
  open, because the chat is mounted once in the shell.
- **The chat's send button is `secondary`.** The sheet stands beside a view that already has its
  primary action, Approve in the detail, and one view shows one primary action.
- **A Bitácora filter returns the reader to page 1.** `ArenaTable` returns to page 1 only when
  the page falls out of range, and it does not slice rows, so the screen keeps the page, slices
  ten rows and resets the page whenever a criterion changes.
- **The settings screen has one save action for all its tabs.** A change in any tab is a draft
  until "Guardar cambios", so no tab saves half a configuration. "Ejecuta" is disabled in every
  autonomy group, and the API refuses it as well ([`../api/AGENTS.md`](../api/AGENTS.md)).

## Commands

Run from this directory, after `npm install`:

| Command | What it does |
|---|---|
| `npm run dev` | regenerates Arena's stylesheets, then serves the app with hot reload |
| `npm run build` | regenerates the stylesheets, typechecks, and builds into `dist/` |
| `npm run typecheck` | typechecks only |
| `npm test` | runs the tests of `src/` with Node's test runner, which strips their types |
| `npm run arena:audit` | regenerates the stylesheets and fails on a rule of Arena's language broken in `src/` |

`arena-to-prod` writes the stylesheets `src/main.tsx` imports; [`../../GENERATED.md`](../../GENERATED.md)
names them. Its contrast and chart-ramp warnings are reported, not failed: the light palette's
ramp has three slots under 3:1 against white, which is why every chart carries direct labels and
a table view.

## Adding a screen

1. Write the component in `src/screens/`, built from Arena components after loading the
   `arena:design` skill.
2. Give it a Spanish route in `src/App.tsx`, inside the shell. A screen the navigation reaches
   also gets an entry in `src/shell/Shell.tsx:DESTINATIONS`.
3. Read its data through a new function of `src/api/http-client.ts`, re-exported by
   `src/api/client.ts`, with its shapes in `src/api/types.ts` following the endpoint's Pydantic
   model. Every number is a `Figure` with a `queryId` the API answers. The endpoint behind the
   function is a row in [`../api/AGENTS.md`](../api/AGENTS.md) before the function exists.
4. Place each piece by who renders it: a piece only this screen renders stays in `src/screens/`
   beside it; a piece another screen or the shell also renders goes in `src/common/`; what wraps
   every route goes in `src/shell/`.
5. Run `npm run typecheck` and `npm run arena:audit`, then the person-run check below.

## Rules of this level

- **A figure on screen carries its source.** Every number links, or expands, to the logged query
  behind it, through `src/common/SentenceWithFigures.tsx:LinkedFigure()` or a sentence whose
  figures `src/common/SentenceWithFigures.tsx:SentenceWithFigures()` links: "how I got here" is
  the third level of every explanation. *No gate holds this.*
- **Severity is a badge with its word**: `src/common/Badges.tsx:Severity()` pairs each tone with
  its Spanish label, so no screen tells severity by colour alone.
- **Every amount and date goes through `src/format.ts`**: pesos as `COP` in `es-CO`, dates spelled
  out in the time zone of Bogotá. The wording is business language; no agent, model or SQL
  vocabulary reaches a manager's screen.
- **A rejection and a request for changes go through `src/screens/ReasonDialog.tsx:ReasonDialog()`**,
  which sends nothing without a reason, and the reason travels in the `Decision`.
- **What the client sends and reads matches the API.** *No gate holds this*, and one place
  breaks it: `decide` sends a `request_changes` as a `reject` carrying the same reason, because
  the API has no `request_changes`, so asking for another proposal closes the alert as rejected.
- **Every screen works by keyboard and at phone width**, with no horizontal scroll.
- **Arena's rules hold in every source file**: tokens only, no class of ours on an Arena
  component, one primary action per view, danger as outline. `npm run arena:audit` holds the ones
  source text can show; the `arena:design` skill states the rest.

## Verified by a person

Open each screen at phone width, walk it by keyboard only, and check that one figure per screen
traces back to its query. Do it in both themes. *No gate holds this.*
