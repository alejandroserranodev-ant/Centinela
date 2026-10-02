# Documenting a private project from its contributor branch

This is a transfer document. It takes what Arena's **contributor** branch does with its
documentation and its gates, and states how much of it a private project should copy. It is
written for an agent asked to document, or re-document, a project in this directory, and for
the person operating that agent.

**A private project has one branch.** Nobody installs it, nobody builds on it, nobody reads its
npm page. Every document in it is written for whoever changes it next, so everything Arena built
for its consumer branch is left behind on purpose, and section 2 says what that is.

The sources are next door. Arena's contributor branch starts at [`arena/AGENTS.md`](https://github.com/dravensoft-dev/arena/blob/main/AGENTS.md) and everything
below cites it from there. Where a private project needs something Arena's branch never did,
because Arena has two readers where a private project has one, or because Arena is not a monorepo,
the rule is stated here in full and says so. A path starting with `arena/` links to that file on
the `main` branch of [Arena's repository](https://github.com/dravensoft-dev/arena), with the
`arena/` prefix standing for its root.

| You are | Read |
|---|---|
| documenting a project that has nothing yet | 1, 3 and 4, then the checklist in 9 |
| documenting a project whose documents have started to drift | 5, then 6 |
| deciding whether a gate is worth writing | 6 |
| checking whether the documentation works | 7 |
| about to copy something from Arena wholesale | 2 and 8 first |

## 1. The premise: one reader, and the reader has the tree

**The reader is whoever changes the project next.** Most often that is an agent starting cold,
with one task and a finite context, and remembering nothing from the session before. Sometimes it
is you, months later, which is the same reader. Private does not mean documented less. It means
documented for one reader instead of two.

Three properties of that reader decide everything below:

1. **It pays for every byte it reads before it can act**, and it cannot tell in advance which
   paragraph was for it. So the entry document routes instead of explaining, and the cost of each
   reading route is measured. That is sections 3 and 6.
2. **It has the tree, and it can run commands.** A consumer of a package cannot, which is why a
   consumer page has to state things. A contributor page can hand over the command that derives
   the answer, and a derived answer cannot go stale. That is section 4.
3. **It has the commit log.** History already has a dated home, so documentation describes what
   the project is and never what it was. That is section 4 as well.

The unit of quality is **how few bytes stand between a question and its answer, and whether that
answer is still true**. The first half is a shape. The second half is a set of gates, because
prose about a tree goes stale silently: the sentence still reads well, every test is green, and a
reader looking for the file it names cannot tell a stale document from their own mistake.

## 2. What you do not build, because nobody consumes the project

Arena carries a great deal of machinery that exists only because it has a second reader. Copying
it into a private project costs maintenance and buys nothing, and a document with no reader is
still the one an agent opens because its name looks authoritative.

| Arena piece | Why Arena has it | In a private project |
|---|---|---|
| the consumer router, [`arena/skills/design/SKILL.md`](https://github.com/dravensoft-dev/arena/blob/main/skills/design/SKILL.md), and the index and prompt tree under it | a builder who uses Arena and never changes it | nothing; there is no builder |
| the branch boundary in [`arena/scripts/check/arena/check-docs.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-docs.ts): `CONTRIBUTOR_PATHS`, `RULE_OWNERS`, `BRANCH_SWITCH` | two branches that must stay disjoint | nothing; one branch has no boundary to hold |
| `CLAUDE.md` as a real file, declared in `DEPARTURES` in [`arena/scripts/check/arena/check-agents-spec.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-agents-spec.ts) | a symlink would answer a builder with the contributor branch | take the convention's own answer: `CLAUDE.md` is a symlink to `AGENTS.md` |
| each package's npm page, the repertoire page with its evidence column, `check:support`, `check:register` | strangers installing a package they cannot read the source of | nothing; keep the evidence idea, which section 4 reuses |
| `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `context7.json`, `llms.txt`, `check:community` | a stranger meeting the repository before any code | nothing; at most one root `README.md`, section 3 says which |
| [`arena/versioning_steps.md`](https://github.com/dravensoft-dev/arena/blob/main/versioning_steps.md) and [`check-release.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-release.ts) | a tag is a promise to every reader of it | keep the shape only, as a sequence document for whatever the project deploys |

**Do not write the consumer half "in case somebody uses it later".** The day somebody does, they
arrive with needs nobody guessed, and the half written in advance is the half that has to be
unlearned first.

## 3. The shape of the tree

### The router

**The root `AGENTS.md` routes and does not explain.** It follows the convention published at
[agents.md](https://agents.md): that name exactly, plain Markdown, one page per level resolved by
proximity, and a command an agent runs because a page listed it. Its body carries four things and
nothing else:

1. **One paragraph saying what the project is, in the vocabulary the whole tree speaks.** Name
   the domain words once and link the page that defines them. [`arena/AGENTS.md`](https://github.com/dravensoft-dev/arena/blob/main/AGENTS.md) does this in its
   opening paragraph (a token layer, two component libraries built on it, a shared Tailwind
   layer), and every page below it can then say *layer* without explaining it.
2. **A table indexed by question.** The first rows are indexed by **symptom**, because a reader
   arriving with a defect does not know yet which part they are changing. The rest are indexed
   by **what you are changing**. Write each row in the words the question actually arrived in.
3. **The sentence "Nothing below the table routes."** It tells the reader that what follows binds
   every change and is read once, not per task.
4. **What binds every change**: the commands, the first step on a fresh clone, and the writing
   rules of section 4.

A minimal router, before any gate exists:

```markdown
# <Project>, for whoever changes it

<Project> is <one sentence>. The words the tree speaks: an **<term>** is <definition>;
the model in full is [`src/domain/AGENTS.md`](./src/domain/AGENTS.md).

**This file routes. Read only what your task needs.**

| I am here because | Start at |
|---|---|
| something renders or behaves wrong and I do not know where it lives | [`src/AGENTS.md`](./src/AGENTS.md), then the level it names |
| a record, a rule of the business, a fixture | [`src/domain/AGENTS.md`](./src/domain/AGENTS.md) |
| a build script or a gate | [`tools/AGENTS.md`](./tools/AGENTS.md) |
| whether the file in front of me is mine to edit | [`GENERATED.md`](./GENERATED.md), before the edit |
| I am about to write down that something is wrong | [`DOUBTS.md`](./DOUBTS.md) |

**Nothing below the table routes.**

A fresh clone runs `bun install && bun run build` first, or part of the tree does not exist.
The commands are the scripts whose name carries no colon: `bun run build`, `bun run test`,
`bun run check`. A colon narrows one of them to a single phase.
```

**A sentence that decides a route gets no inversion, no ellipsis and one clause at most.** The
prose style Arena uses elsewhere is dense and memorable, and in a routing row an opaque sentence
costs the wrong branch. Arena holds that register with `check:register` on its consumer pages
only: thirty words per sentence, one subordinate clause, a named subject. In a private project the
router table is where it pays.

### The levels

**A directory that owns decisions gets its own `AGENTS.md`.** Its job is to state that level's
rules and to carry a table saying why each file in it exists. [`arena/scripts/AGENTS.md`](https://github.com/dravensoft-dev/arena/blob/main/scripts/AGENTS.md) is the
model: the path answers what phase a script belongs to and what it may touch before the file is
opened, and an exception to the grid is written where it applies, because an exception with no
argument beside it is how a grid stops meaning anything.

- **A level is reachable by a link from the router, and not only by being nearest.** Proximity
  hands an agent the closest page and hands a person nothing. `check:agents` holds this.
- **A level is earned.** Add one when a directory holds decisions a reader of its parent does not
  need. A level that starts summarising its siblings has stopped being a level.
- **Where a level needs two documents, split by audience and never by topic.** The `AGENTS.md`
  is the half that **decides**, and a sibling is what a reader **consults** while doing the work.
  [`arena/contracts/AGENTS.md`](https://github.com/dravensoft-dev/arena/blob/main/contracts/AGENTS.md) states it: [`api/AGENTS.md`](https://github.com/dravensoft-dev/arena/blob/main/contracts/api/AGENTS.md) decides whether a member should exist,
  [`api/MemberForms.md`](https://github.com/dravensoft-dev/arena/blob/main/contracts/api/MemberForms.md) is the vocabulary a member is written in. Declare each sibling where a gate
  reads it, as `SHAPE` does in [`arena/scripts/check/arena/check-contracts.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-contracts.ts), so an undeclared
  one fails instead of sitting invisible.
- **A level's own tour lives in that level.** The router and the parent carry the cross-level rule
  and a pointer. This is also how every size budget is bought back later.

### The root companions

Three documents sit beside the router, and each answers one question every change asks.

**`GENERATED.md`: which half of this file is mine.** An edit to a generated region survives until
the next build and then goes, and nothing fails in between. [`arena/GENERATED.md`](https://github.com/dravensoft-dev/arena/blob/main/GENERATED.md) sorts every file
into three kinds: generated with a name that says so (`<stem>.generated.<ext>`), generated with a
name that does not (a banner on the first line, or an entry in a reason-carrying list), and
authored with a region a machine writes inside it, which is the kind that costs. It closes with
the rule that makes the page cheap to trust: after a build, `git status --short` is the list of
what the generators decided to write. **A file you did not expect means a generator you did not
know reads what you edited. A file you expected and did not get means your source is in the wrong
place.** Derive the list of generators from the tree rather than writing it down, as that page
does with one command.

**`DOUBTS.md`: what counts as a debt, and where it goes.** Section 5 is its content.

**One sequence document per irreversible procedure**: a deploy, a release, a migration of live
data. [`arena/versioning_steps.md`](https://github.com/dravensoft-dev/arena/blob/main/versioning_steps.md) is the model. It is the order the moves are made in, and **every
step is a step because skipping it fails something or, worse, fails nothing**. Each place to edit
is named by what it says and never by a line number. Each verification gives its expected output,
including the failure that is expected at that step, so a reader can tell the right red from the
wrong one.

### `CLAUDE.md`, `README.md` and process documents

**`CLAUDE.md` is a symlink to `AGENTS.md`.** [`arena/CLAUDE.md`](https://github.com/dravensoft-dev/arena/blob/main/CLAUDE.md) is a real file only because it
chooses between two branches, and it carries no rule of its own. A private project has no choice
to offer, so the symlink is the whole file.

**At most one `README.md`, at the root, and it carries no rule.** It is what a forge renders on
the repository page. Point it at the router, and declare it where `check:agents` reads its
survivors, with the reason, so a second README anywhere else fails.

**Specs and plans are dated and deleted once executed.** Arena files them under
`docs/superpowers/` as `YYYY-MM-DD-<name>.md`, and a spec written ahead of its plan carries a
`-pending-N` suffix until the plan exists. **A permanent document never cites one**, because the
citation is condemned the day it is written, and debt filed inside a plan dies with the plan.
`check:citations` in Arena refuses a citation into a root git ignores for the same reason: it
resolves on the machine that wrote it and on no clone.

## 4. The rules a page is written by

Each rule carries its reason and names what holds it. A rule no gate holds says so, because a
reader who does not know which tier a rule is in assumes the build will catch it.

- **A fact lives in exactly one page: the level that owns the code it describes.** A restatement
  one level up fails nothing, so it is the copy that goes stale. A rule binding several parts is
  stated once, at the level above them. *No gate holds this.*
- **Documentation is written in the present tense.** It describes what the project is, never what
  it was, what a name used to be, or which part is newest. The reason a rule exists is not history
  and stays: state it as a property of the thing, not as an incident. *No gate holds this*, so the
  verification list ends with an end-to-end read of what changed.
- **The commit log is where history goes, so a commit message carries the reason.** Arena's
  subjects are sentences about what the tree now does and why: "A corpus is built once and read
  seven times, so the reference case stops rebuilding it per reference". A message with a backtick
  is written through a quoted here-doc, `git commit -q -F - <<'MSG'`, because a backtick inside a
  double-quoted `-m` is spliced away by the shell without an error.
- **No document carries a literal count of anything that grows.** Hand over the command that
  produces it instead. Two exceptions: a number an assertion holds, like the gate table in
  [`arena/scripts/check/AGENTS.md`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/AGENTS.md), which [`check-all.test.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-all.test.ts) derives and compares and which is the
  only exception Arena admits; and a count in the sentence that enumerates what it counts, because
  a reader can check it on the spot. Admit the second one too: a private project's router names
  its few parts in one sentence more often than Arena's does. A measurement is not a tally and
  stays.
- **Prose cites code as `path/to/file.ts:member(parameters)`, never by line number.** A line moves
  under the next edit and a member carries its own address. `check:citations` holds both halves,
  and **the member half is the one that goes wrong quietly**: the wrong file with the right member
  sends a reader somewhere confident and empty.
- **Never describe a file you have not read.** A grep answers where a name appears and never what
  the file around it says. [`arena/DOUBTS.md`](https://github.com/dravensoft-dev/arena/blob/main/DOUBTS.md) names the three shapes a false claim takes, none of
  them findable by keyword: a document describing its own layout, a component named in *another*
  file's prose, and a sibling cited by its bare filename, which a refactor rewrites in every import
  and in no sentence. When you change `X`, read every hit of a grep for `X` across the documents,
  and scope that worklist by its path list, never by piping `grep -n` through `grep -v`, which
  filters hits by their text.
- **Say what nothing verifies.** Every claim sits in one of three tiers: refused by a gate,
  reported but allowed, or held by a person. Where a claim is about something working, give it an
  evidence level: held by a gate, verified once by hand, or allowed and never exercised. The last
  is a complete and honest answer, and promoting a claim without exercising it is the failure the
  level exists to prevent. The router ends with a verification list of the checks only a person
  runs, each naming the page that explains what they are looking at. Arena states each such check
  in the level that owns it instead, as [`arena/frameworks/AGENTS.md`](https://github.com/dravensoft-dev/arena/blob/main/frameworks/AGENTS.md) does for a manifest against
  its contract, and has no list; in a router small enough to read whole, the list is what makes
  every change ask every check.
- **A decision carries its reason, and a departure from a convention is written down.** A decision
  without its reason is worthless, because the reason is the whole entry. Arena lists each place it
  departs from the convention it follows, with the measurement that pays for it, since a departure
  nobody recorded is one the next reader repairs.
- **Hand-written source carries no comments.** Scripts and tests may carry one header, at most ten
  lines. The name carries the context, and a comment is prose nothing checks. Knowledge a rename
  cannot express (a measurement, a vendor's behaviour, a pinned version, a constraint of a test
  environment) goes in that header, in a gate's reason string, or in the level's page, **somewhere
  a stale copy of it fails something**. The one carve-out Arena allows is a comment a gate holds
  equal to its source, which cannot go quietly false. `check:docs` holds the rule with a lexer, so
  a `//` inside a string is not a comment.
- **Commands are spelled as the nearest manifest declares them.** A page under an app names that
  app's scripts, not the root's. `check:vocabulary` holds it.
- **A house style rule is only a rule if something holds it.** Arena bans the em dash in prose and
  `check:docs` enforces it outside fences and code spans. Keep it or drop it; the lesson is that a
  style rule nobody holds decays into a preference within a month.

## 5. Records that fail, and where a debt goes

**A debt is paid, or made loud, before it is written down.** [`arena/DOUBTS.md`](https://github.com/dravensoft-dev/arena/blob/main/DOUBTS.md) is not a ledger:
it defines what a debt is and says where the records live. Three tests separate a debt from an
ordinary imperfection: it is a claim about the tree, not a preference; it survives the person who
found it; and it costs something specific, with the cost stated.

The places a debt goes, in order of preference. Each of the first five fails when it stops being
true, and a paragraph does not:

1. **Pay it.** A defect that can be fixed is work, not debt.
2. **A gate with a reason-carrying map.** `EXEMPT`, `COVERED`, `UNTRACKED`, `SURVIVORS`: each
   entry names a case and says why, **as a string value rather than a comment**, and the gate's
   own suite asserts on the map by name. **A stale entry fails the gate**, so the exception cannot
   outlive the thing it excused.
3. **A suite assertion.** An assertion that a collision does not happen is worth more than a
   sentence saying it does not.
4. **The level's own `AGENTS.md`**, where the rule the limit qualifies is stated.
5. **The one header** a script or a test is allowed.
6. **A paragraph in `DOUBTS.md`**, written as what is wrong, what it costs, and the command that
   re-derives it. Arena's filed entries all read that way: "Nothing server-renders an Angular
   page", then who pays and where it lands, then the command.

**An empty map is a claim.** Arena keeps several at zero on purpose (`ALLOWED` in the pixel
comparison, `HARNESS_KEYS`, the owner list for locale ordering) and states that the emptiness is
the claim. A suite asserting the map is empty turns "we have no exceptions" into something that
fails the day one appears.

**Agent memory is not a record.** It fails nothing, it lives on one machine, and no other reader
sees it. A memory that describes the tree ("a worktree under `.claude/` makes one gate fail with
thirteen spurious problems") is a debt nobody filed: move it into the gate, a suite or `DOUBTS.md`,
and let the memory point there.

## 6. Gates

### The shape of one

A gate states one claim about the tree and fails when it stops being true. Arena's gates share one
shape, and the shape is what makes the rest possible. Reduced to one file, with the shared walk it
imports:

```ts
import { walk } from './tree.ts';

export const EXEMPT = new Map<string, string>([
  ['legacy/notes.md', 'kept for the audit trail the accountant asks for; nothing links it'],
]);

export function zeroScanProblems(documents: string[]) {
  return documents.length === 0
    ? ['walked 0 documents, so every rule below passes over a tree it never opened']
    : [];
}

export function staleProblems(documents: string[]) {
  return [...EXEMPT.keys()]
    .filter((path) => !documents.includes(path))
    .map((path) => `EXEMPT names ${path}, which the tree no longer holds: ${EXEMPT.get(path)}`);
}

export function problems(documents = walk().filter((p) => p.endsWith('.md'))) {
  return [...zeroScanProblems(documents), ...staleProblems(documents), ...claimProblems(documents)];
}

if (import.meta.main) {
  const found = problems();
  for (const one of found) console.error(one);
  process.exit(found.length === 0 ? 0 : 1);
}
```

- **The logic is pure functions returning problem strings**, and `claimProblems` is the one that
  states the gate's own claim; the guard prints and exits and does nothing else.
  That is what lets a suite assert on the map by name without running the gate. The work sits
  behind the main guard, so importing the file runs nothing.
- **A registry and a runner.** Every gate is in one `GATES` list and `bun run check` runs all of
  them without stopping at the first failure, so one sweep reports every problem. **A gate has two
  existences, the file and every place that invokes it, and only the second is worth anything**:
  a gate registered nowhere passes forever. Arena's [`check-all.test.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-all.test.ts) asserts the registry by
  literal value, so adding a gate is a two-file change on purpose.
- **A gate that finds nothing reports zero violations either way.** Make a zero-result count an
  explicit failure. Decide absence by walking the tree, never by probing a constructed path, which
  cannot tell "absent" from "not found". After anything moves, the question is not whether the gate
  still passes but how many things it looked at.
- **One answer to "what is not this tree".** In a private project, make it one walk every gate
  asks: a `tree.ts` holding the walk and the one set of names it skips. Arena keeps its walks
  separate but names the foreign directories once, in
  [`arena/scripts/lib/arena/foreign-trees.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/lib/arena/foreign-trees.ts), and a suite fails a script spelling them again.
  Section 8 says what a second spelling cost.
- **A suite plants one violation per rule.** A gate only ever seen to pass is a gate seen to do
  nothing. Arena's portability suite found a rule that never fired this way.
- **A gate judges and does not emit.** A gate that writes a file becomes an input to another, and
  a sweep then stops reporting every problem in one pass.
- **A gate that cannot run says so, in one spelling.** Arena exits 2 for a missing dependency,
  reports SKIP, and marks the run INCOMPLETE; the repository then declares itself strict, so a
  skip fails. The decision lives in one function, because each gate spelling its own made one
  missing browser fail one gate and skip the next.
- **The full sweep is a completion gate, not a per-commit toll.** Run single gates while working
  and the whole of `bun run check` once, when the work is finished. Saying so is what lets a gate
  be expensive enough to be worth having.

### Which gates a private project needs, in the order they pay off

| Gate | Fails when | Pays off when |
|---|---|---|
| `check:agents` | an `AGENTS.md` no chain of links from the router reaches, or a `README.md` outside the declared survivors | the tree has more than two levels |
| `check:citations` | prose names a file that is not there, or cites `file:member()` where the file declares no such member | from the first document; it is the cheapest and it finds the most |
| `check:vocabulary` | a page tells a reader to run a script the nearest manifest does not declare, states a naming convention no file answers to, or hands over a `find` whose pattern matches nothing | the first time a script is renamed |
| `check:docs` | a document passes the size cap or a table cell passes its own, or a hand-written source carries a comment, or prose breaks a house style rule | the first document that grows past a comfortable read |
| `check:generated` | a file a script writes is not named `.generated.`, or is neither tracked nor covered by a reason-carrying ignore entry | the project has generators |
| `check:routes` | a declared reading route costs more characters than its budget, or has fallen far under it | the router passes about 10 KB, or a route has three stops |
| a count assertion | a number written in a document disagrees with what the tree derives | a document states a count at all |

The first four and the shared walk are a small port next to Arena's gates, suites included. A
private project that is a monorepo needs three rules on top of them that Arena never needed,
because Arena is not one:

- **A path in prose resolves from the root, from beside the page, or from the root of the package
  holding the page**, so a page inside an app names its own files by their tail and survives the
  app being moved.
- **A command resolves against the manifest nearest the page naming it**, the way the convention
  resolves the nearest `AGENTS.md`.
- **An entry point is named by the page beside its own manifest**, and a manifest with entry
  points and no page beside it fails.

**Do not port Arena's other gates.** Most of Arena's gates hold a design language across two
framework layers. A private project needs the documentation gates above, plus a gate for each
failure of its own that ships green: a sweep for horizontal overflow at phone width is the kind,
and the list comes
from the defects the project has actually had, not from Arena's.

### The size cap and the byte budget

**One shared cap per document, 60,000 characters in Arena, measured in characters and never in
bytes.** A named allowance raises it for one document and carries its reason. **An allowance is not
an exemption**: the document is still measured against the raised number, and one that falls back
inside the shared cap fails as a stale allowance, so decomposing a document returns the pressure
instead of ending it.

**A byte budget per reading route** is the practice nothing else in a normal CI can replace,
because documentation grows by a paragraph that reads as an improvement where it is written and
costs every reader of that route, once per task. `ROUTES` in
[`arena/scripts/check/arena/check-routes.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-routes.ts) is the model:

- **The router is declared once, in `ENTRIES`, with a budget of its own.** A route is what a
  reader pays past it. Arena first charged its router to every route that opened with it, so one
  paragraph was argued seven times.
- **A stop is a pathspec charged for the largest file it reaches**, so the figure is the worst case
  a reader meets, not an average nobody experiences. A route where the reader answers a question and
  walks one way declares branches and is charged its worst branch.
- **A budget the route has fallen under by more than 15% fails as stale.** Otherwise the saving is
  spent by the next paragraph nobody argued for.
- **Every budget carries its reason as a string, and the string is held too.** A reason says why
  the number is right today, so it names no figure, never says "raised", and stays short.
  Section 8 says what it turns into otherwise.

For a private project, start the contributor router near 8 to 10 KB. Arena's is about 23 KB, paid
in full on every task including the one-line ones.

## 7. Testing whether the documentation works

Gates prove the documents are consistent with the tree. They do not prove a reader finds the
answer. **Cold walks** do, and they are the cheapest evidence there is.

- **Give a fresh agent one real task and the tree, and nothing else.** Take the task from a
  router row, or better, from a symptom. Record which row it picked, how many characters it read
  before its first edit, and the one sentence it returns about what it could not find.
- **Run several and compare the walks, not the results.** Two walks taking different rows for the
  same task is an ambiguous row. Arena's contributor router gained its symptom rows this way: in
  nine cold walks, one found two equally correct rows for a keyboard defect and picked by luck, and
  one planned a component that already shipped, because no row asked whether it existed.
- **A clean sweep deserves suspicion.** After a run, inject known defects into a copy of the output
  and confirm the check fires on each. A mutation that fails to apply is a hard error, never a
  silent no-op.
- **Audit the transcript, not the self-report.** In Arena's own measurement an agent reported five
  calls and had made six. Keep the prompts byte-identical between runs so two runs are comparable.
- **A number that does not move after a fix is a question about the route.** When Arena fixed a
  link and its measurement stayed flat, the cause was the search index ranking every match equally,
  not anything the documents said.

## 8. Where Arena's contributor branch bites, and what to do instead

Copy the structure. Do not copy these. The first three are defects Arena carried with every gate
green; each is fixed now, and each fix is a rule to copy on day one rather than after.

**1. Reason strings turn into changelogs.** The present-tense rule reached `.md` files and nothing
else, so the budget reasons in [`arena/scripts/check/arena/check-routes.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-routes.ts) grew to about 78,000
characters across eighteen routes, more than the cap allows any document, and said "Raised" 95
times; four of them ended by admitting that every figure above named a number the route no longer
had. **A reason states why the value is right today. What it was, and why it moved, belongs to the
commit that moved it.** Arena now rewrites them in the present and `reasonProblems` fails a reason
that names a budget figure, says "raised" or "lowered", or runs past a length.

**2. A cap becomes the target.** [`arena/scripts/check/arena/AGENTS.md`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/AGENTS.md) sat 153 characters under
its 60,000 cap, with single rows of its gate table near 4,000 characters. A cap on a document does
not cap a row. **A table cell that needs a paragraph is a level that was never written**: keep the
claim in the row and move the argument to where it is enforced. Arena now caps a table cell at
2,000 characters in `check:docs`, and the rows that broke it lost their histories rather than their
claims.

**3. Every walk spells what it skips.** Arena had about twenty skip sets, and the root walks of
`check:vocabulary`, `check:routes` and the script graph missed `.claude`, so a git worktree there
was read as a second copy of the tree: `check:vocabulary` failed on thirteen problems that were not
in the tree, and `check:routes` measured 469 documents instead of 234. One module now names the
foreign directories and a suite fails any other spelling.

**4. The router's fixed cost.** Arena's contributor router is paid in full on every task. Its
rules section is the part to push behind a link when most tasks are small, keeping the table and
the commands in the body. Measure it with the entry budget rather than guessing.

**5. The rule no gate holds is the one that decays.** Present tense and one-fact-one-page are both
unheld in Arena, by necessity. Put them last in the verification list, as an end-to-end read of
what changed, so they are at least asked once per change.

## 9. Adoption, in three steps that are each a place to stop

A project on the first step is documented correctly and is not waiting to finish. What the later
steps buy is stated so a project can decline them on purpose.

**Step one, the shape.** Costs an afternoon, and one page that must stay accurate as everything
under it moves.

- [ ] A root `AGENTS.md` that routes: one paragraph of vocabulary, a question table with symptom
      rows first, "Nothing below the table routes", then the commands and the rules.
- [ ] `CLAUDE.md` as a symlink to it, and at most one root `README.md` pointing there.
- [ ] One `AGENTS.md` per directory that owns decisions, each linked from the router or a parent.
- [ ] `GENERATED.md` and `DOUBTS.md` beside the router, and a sequence document for each
      irreversible procedure.
- [ ] The rules of section 4 stated once, in the router, each saying what holds it.
- [ ] A verification list of the checks only a person runs, ending with the end-to-end read.

**Step two, the gates.** Costs real engineering, and gates that fail your own pull requests,
which is the point.

- [ ] One shared walk, a `GATES` registry and a runner that reports every failure in one pass.
- [ ] `check:citations`, `check:agents`, `check:vocabulary`, `check:docs`, each with a suite that
      plants a violation per rule and asserts every map by name.
- [ ] A zero-result failure in every gate, and a stale-entry failure on every map.

**Step three, the measurements.**

- [ ] `check:routes` with the router in `ENTRIES`, a budget and a present-tense reason per route,
      failing high and failing stale-low.
- [ ] `check:generated` once the project has generators.
- [ ] A cold walk after any change to the router, and a mutation test whenever a run comes back
      clean.

If you take one thing, take the question table with its symptom rows. If you take two, add
`check:citations`. Everything else here is a refinement of those.

## A note on where this file lives

This file sits outside every repository on purpose. It describes a practice rather than a tree, so
no citation gate, budget or cap applies to it, and its paths are true of this directory the day it
was written and of no clone. **The moment a practice is copied into a project, it stops being this
file's concern and becomes that project's**, and the gates are what hold it there.

If you file it inside a repository later, check the charter of the directory first. Arena's
`docs/` is declared as `DATED_PROCESS_DOCUMENTS` in [`arena/scripts/check/arena/check-docs.ts`](https://github.com/dravensoft-dev/arena/blob/main/scripts/check/arena/check-docs.ts),
exempt from the size and prose gates because a spec or a plan is deleted once executed. A document
meant to last, filed under a charter that says it will not, is the failure this page exists to
describe.
