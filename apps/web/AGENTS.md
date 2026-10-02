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
  agents work.
- **The screens run on a simulated API until `apps/api` serves one.** `src/api/client.ts` mirrors
  the minimal API with one function per endpoint, streams agent progress and chat as async
  iterators shaped like SSE events, and reveals each alert when the simulated day reaches its date.
  It is replaced by a fetch client without touching a screen. `src/api/types.ts` is a draft
  contract: `apps/api`'s Pydantic models are the source, and these types follow them. Every number
  travels as a `Cifra` with its `consultaId`, so the type itself asks each figure for its query.
- **The fixtures in `src/api/fixtures/` are illustrative.** They are built from the brief's public
  example (the margin of line `Hogar`, supplier X, $42 M a month) and from entities named as
  examples, never from the dataset, because figures read from `data/csv/` would name the seeded
  scenarios (see the scenarios section of [`../../data/AGENTS.md`](../../data/AGENTS.md)). Each
  figure cites an example query against a real `v_*` view, so "how I got here" has something to
  show; the queries are not run.
- **The screen computes no figure.** The inbox totals (money at risk today, decisions pending,
  recoverable per month) are sums over alerts rather than a `v_*` view, so the API computes them
  and sends each as a `Cifra` whose query reads the alerts table, which is why `Consulta.vista`
  also takes `alertas`. A sum taken on screen would be a figure with no query behind it.
- **A notice closes after five seconds, with or without an action**, where Arena's own queue waits
  4.2 s, or 7 s for a notice that carries an action. The demo lasts five minutes, and a stack of
  notices covers the reading column. A danger notice still stays until it is closed, by Arena's
  rule `arenaToastDelay`, which `src/estado/Simulacion.tsx:useAvisos()` applies with the shorter
  interval.
- **Each chart sits in a box that clips sideways.** `ArenaLineChart` hides its accessible table in
  a one-pixel box, but a table lays out to its content anyway, and at phone width that box widened
  the page. Clipping the inline axis alone keeps the tooltip whole.

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
