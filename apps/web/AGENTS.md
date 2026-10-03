# apps/web: the decision inbox

This level is Centinela's interface: a **decision inbox, not a dashboard**. It holds the scaffold
the screens are built on and the skin they wear. Which screens exist and what each shows is
[`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its screens section.

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
  there. Serve it over HTTP, because opened from `file://` its stylesheet does not load.
- **Agent progress arrives by SSE** from the API, so the screen shows the step in course while the
  agents work. Chat and `/simulacion/avanzar` stream events as `text/event-stream`.
- **The screens connect to the real `apps/api` via HTTP.** `src/api/http-client.ts` implements
  the fetch client with one function per endpoint, streams agent progress and chat as async
  iterators, and talks to the API using Pydantic models from `apps/api`. `src/api/types.ts` is
  the contract: synchronized with `apps/api/src/centinela_api/modelos.py`, field for field.
  Every number travels as a `Figure` with its `queryId`. Configuration lives in `src/api/config.ts`;
  use `VITE_API_URL` environment variable to point to a different API (`.env.example` shows how).
  The HTTP client is drop-in compatible with the old fixture-based one: screens never knew the
  difference.
- **Code is written in English; what a person reads stays in Spanish.** Files, components,
  functions, types, props, state keys and our own CSS classes are English. Every text on screen,
  including `aria-label`s, hints and notices, is Spanish, and so is the displayed content of the
  fixtures. The words the data names keep their Spanish in code too: the agents (`vigia`,
  `analista`, `estratega`, `ejecutor`), the metrics (`margen_pct`…), the `v_*` views and the
  `alertas` table, because a translation would make a second name for one thing.
- **The draft contract is English except its routes.** Field names and values in
  `src/api/types.ts` are English (`status: 'proposed'`, `severity: 'critical'`), so the
  `apps/api` models and the web read one vocabulary of code. The endpoint paths and their query
  string stay as the brief writes them (`/simulacion/avanzar`, `/alertas?estado=propuesta`,
  `/alertas/{id}/decision`, `/chat`, `/bitacora`), because the jury calls them by those names;
  where the brief's query string carries a lifecycle value, the fetch client sends the brief's
  spelling.
- **The web's own routes are Spanish** (`/alertas/:id`, `/bitacora`, `/configuracion`), because the
  address bar is on screen during the demo and the paths mirror the API and the brief's screen
  names.
- **Ids and data keys are English** (`alert-hogar-margin`, `q-hogar-drop`, `v_margen_semanal_linea`);
  domain words stay in Spanish as the dataset names them. An id never reaches a manager's screen.

## Running the web with the API

1. **Start the API** (see [`../api/AGENTS.md`](../api/AGENTS.md)):
   ```bash
   cd apps/api
   pip install -e .
   uvicorn centinela_api.main:app --reload
   ```

2. **Configure the web** to connect to the API:
   ```bash
   cp .env.example .env
   # Edit .env if needed (default: http://localhost:8000)
   ```

3. **Install and run**:
   ```bash
   npm install
   npm run dev
   ```
   Opens on http://localhost:5173

4. **Use Swagger UI** to test the API directly:
   http://localhost:8000/docs

The web will:
- Fetch simulation state on load (`GET /simulacion/dia-actual`)
- List alerts (`GET /alertas?estado=propuesta`)
- Stream day advances (`POST /simulacion/avanzar` with SSE)
- Stream chat answers (`POST /chat` with SSE)
- Post decisions (`POST /alertas/{id}/decision`)
- Read bitácora (`GET /bitacora`)

**Before Vigía is implemented**, the `/simulacion/avanzar` endpoint will move the clock but return
no new alerts. The web can still:
- Display existing alerts (none until seeded)
- Decide on alerts
- View the audit log
- Use chat (dummy response)

The fixtures in `src/api/fixtures/` are **no longer used**; they can be removed once the API
provides test data.
  examples, never from the dataset, because figures read from `data/csv/` would name the seeded
  scenarios (see the scenarios section of [`../../data/AGENTS.md`](../../data/AGENTS.md)). Each
  figure cites an example query against a real `v_*` view, so "how I got here" has something to
  show; the queries are not run.
- **The screen computes no figure.** The inbox totals (money at risk today, decisions pending,
  recoverable per month) are sums over alerts rather than a `v_*` view, so the API computes them
  and sends each as a `Figure` whose query reads the alerts table, which is why `Query.source`
  also takes `alertas`. A sum taken on screen would be a figure with no query behind it.
- **A notice closes after five seconds, with or without an action**, where Arena's own queue waits
  4.2 s, or 7 s for a notice that carries an action. The demo lasts five minutes, and a stack of
  notices covers the reading column. A danger notice still stays until it is closed, by Arena's
  rule `arenaToastDelay`, which `src/state/Simulation.tsx:useToasts()` applies with the shorter
  interval.
- **Each chart sits in a box that clips sideways.** `ArenaLineChart` hides its accessible table in
  a one-pixel box, but a table lays out to its content anyway, and at phone width that box widened
  the page. Clipping the inline axis alone keeps the tooltip whole.

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
- **The settings screen has one save action for its three tabs.** A change in any tab is a draft
  until "Guardar cambios", so the three tabs never save half a configuration. "Ejecuta" is
  disabled in every autonomy group, and the API rejects it again with a 422.

## Commands

Run from this directory, after `npm install`:

| Command | What it does |
|---|---|
| `npm run dev` | regenerates Arena's stylesheets, then serves the app with hot reload |
| `npm run build` | regenerates the stylesheets, typechecks, and builds into `dist/` |
| `npm run typecheck` | typechecks only |
| `npm run arena:audit` | regenerates the stylesheets and fails on a rule of Arena's language broken in `src/` |

`arena-to-prod` writes the stylesheets `src/main.tsx` imports; [`../../GENERATED.md`](../../GENERATED.md)
names them. Its contrast and chart-ramp warnings are reported, not failed: the light palette's
ramp has three slots under 3:1 against white, which is why every chart carries direct labels and
a table view.

## Rules of this level

- **A figure on screen carries its source.** Every number links, or expands, to the logged query
  behind it: "how I got here" is the third level of every explanation. *No gate holds this.*
- **Severity is never told by colour alone**: a label or an icon carries it too.
- **Money is Colombian pesos, dates are explicit, and the wording is business language.** No
  agent, model or SQL vocabulary reaches a manager's screen.
- **Reject asks for a reason**, and the reason is sent with the decision.
- **Every screen works by keyboard and at phone width**, with no horizontal scroll.
- **Arena's rules hold in every source file**: tokens only, no class of ours on an Arena
  component, one primary action per view, danger as outline. `npm run arena:audit` holds the ones
  source text can show; the `arena:design` skill states the rest.

## Verified by a person

Until a gate exists: open each screen at phone width, walk it by keyboard only, and check that one
figure per screen traces back to its query. Do it in both themes.
