# Start here

This guide is for a developer who does not know Centinela yet. Read it top to bottom once: it goes
from what the challenge asks, through how the parts connect and what binds every change, to each
part's decisions, the two designs that bind the agents next, and what runs today.

## The reading order

| Page | The question it answers |
|---|---|
| [The challenge](../../../docs/challenge/AGENTS.md) | what Centinela must do, for whom, and what the jury tests |
| [The project](../../../AGENTS.md) | the words every page speaks, how the parts connect, and the rules every change follows |
| [How an alert crosses the parts](./alert-journey.md) | one alert followed from the clock to the log, in three diagrams |
| *The levels* | what each part decides, from the data up to the screen, then the evaluation set |
| [The decision tree](./decision-tree.md) | how the orchestrator decides who goes next, on which standards, and how the tree grows |
| [The KPI kernel](./kpi-kernel.md) | where every business measure comes from, and how a new one is born without any agent writing to a database |
| [What exists today](./status.md) | what is code, what is only decided, and what is roadmap |
| *Conventions* | which files a machine writes, where a debt goes, and how a page is written |

The project page is written for whoever changes the repository: its table routes a task to the
page that owns it. Here it is read once, for its vocabulary, its picture of the chain and its rules.

## The three states of a claim

Each claim is *Implemented*, *Decided, not implemented*, or *Roadmap*. A chapter or section that
describes a design with no code carries a warning box saying so. [What exists today](./status.md)
is the one page that sorts the parts into the three states, and it is built from the commit the
guide was published from.

## How this guide is made

Nothing here is written in Docmost. Every page is published from the repository by
`docs/guide/publish.py`: the level pages and the root companions are copied as they are, and the
chapters live in `docs/guide/chapters/`. The box under each title names the source file and the
commit. An edit made here is lost on the next publish; a correction goes into the repository.
