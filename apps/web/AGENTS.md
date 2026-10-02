# apps/web: the decision inbox

This level is Centinela's interface: a **decision inbox, not a dashboard**. It holds no code yet;
this page states the decisions the code is written against. Which screens exist and what each
shows is [`../../docs/challenge/AGENTS.md`](../../docs/challenge/AGENTS.md), its screens section.

## Decisions

- **Next.js with React, built on Arena React.** Arena is Dravensoft's design system; Centinela
  declares its own skin in an `arena.config.json` and answers Arena's style roles with its own
  style plugin, instead of styling components by hand. Load the `arena:design` skill before building
  or changing a screen. Charts follow the `dataviz` skill.
- **Agent progress arrives by SSE** from the API, so the screen shows the step in course while the
  agents work.

## Rules of this level

- **A figure on screen carries its source.** Every number links, or expands, to the logged query
  behind it: "how I got here" is the third level of every explanation. *No gate holds this.*
- **Severity is never told by colour alone**: a label or an icon carries it too.
- **Money is Colombian pesos, dates are explicit, and the wording is business language.** No
  agent, model or SQL vocabulary reaches a manager's screen.
- **Reject asks for a reason**, and the reason is sent with the decision.
- **Every screen works by keyboard and at phone width**, with no horizontal scroll.

## Verified by a person

Until a gate exists: open each screen at phone width, walk it by keyboard only, and check that one
figure per screen traces back to its query.
