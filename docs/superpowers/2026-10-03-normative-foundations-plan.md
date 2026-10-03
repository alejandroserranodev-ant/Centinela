# Normative foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write spec 1's foundations into the permanent pages: two vocabulary terms, one sentence and two rules in the root `AGENTS.md`, the registry `packages/agents/arbol/fundamentos.yaml` with the clauses spec 1 cites, and the debt of the unverified clauses in `DOUBTS.md`.

**Architecture:** No code. Four permanent files change or appear, and the spec is renamed now that its plan exists. Every edit is an exact sentence given below; the verification of each task is the person-run list at the end of the root `AGENTS.md` (link check, `git status --short` against `GENERATED.md`, end-to-end read).

**Tech Stack:** Markdown, YAML, `git`, `grep`, `awk`.

**Spec:** `docs/superpowers/2026-10-03-normative-foundations.md`. Read it whole before Task 2. The other five specs in `docs/superpowers/` are not planned here; Tasks 2 and 3 name the points where they constrain this plan.

## Global Constraints

- Documentation is in English; domain words stay in Spanish, in backticks, as the data names them (`Vigía`, `bitácora`, `fundamento`, `detectar`).
- Documentation is in the present tense. No page says what was, what is new, or what a later spec will do.
- A fact lives in exactly one page. No permanent page restates a table of the spec.
- **No permanent page cites a spec or a plan**, by path, by number ("spec 4") or by name (`normative-foundations`). Only `docs/superpowers/` files may.
- No literal count of anything that grows: no "eighteen clauses", no "four standards". A count in a sentence that enumerates what it counts is admitted.
- Prose cites code as `path:member(parameters)`, never by line number.
- Each rule in the root says what holds it; every rule added here ends in `*No gate holds this.*`
- Hand-written source carries no comments: `fundamentos.yaml` has no `#` line.
- No text of an ISO standard is invented: an entry names a clause only as spec 1 names it, and an entry for which spec 1 names no clause number carries none.
- Commit messages are short sentences that carry the reason, written through `git commit -q -F - <<'MSG'` when they contain a backtick (`docs_guide.md` §4). **No commit is made without asking the user first.**

## Decision: Task 2 creates the registry, with only the clauses spec 1 cites

`packages/agents/arbol/fundamentos.yaml` is created by this plan, not by spec 2's. Reasons:

1. **The debt spec 1 files carries a command that reads the file.** `DOUBTS.md` requires every filed debt to end with "the command that re-derives it"; filed without the file, that command prints `No such file or directory` on the day it is written, and a record whose command fails from birth is the paragraph `DOUBTS.md` warns against.
2. **The new root rule names the registry**, and a reader of the root has to be able to open it. The rule links the file, and the link check of the root's verification list fails on a link to a missing file.
3. **The registry is spec 1's artefact by its own scope table**: "What never grows at runtime" lists it, and "only a person adds to the registry" is spec 1's rule. Spec 2 consumes it (its validator refuses a `fundamento` absent from it) and fixes the tree beside it; it does not define it.

What spec 2 keeps: the policy-section entries (such as `fin-pol-004.s4`, its first example), which enter when the first node that cites them is written, so no entry sits in the registry with nothing citing it; the page text in `packages/agents/AGENTS.md` that says where the registry lives (spec 2's "Pages this spec changes" owns that section); and the validator.

What the registry leaves out, with the reason:

- **The brief's golden rule**, which spec 1 gives as half the `fundamento` of the first law: it is the challenge's requirement, not a clause of a standard or a policy section, and the root rule "SQL or Python computes every number" already holds it. Its standard half, ISO 9001 §7.5, enters.
- **Goal-Question-Metric**: spec 1 admits it as the test a new KPI passes, not as a `fundamento` a node or a KPI rests on.
- **ISO 9001 §10.2.1 e) and f)**: spec 1's standards table names "a) to f)", but no stage and no law rests on e) or f).

The entry shape is `id`, `cita`, `funda`:

- `id` is lowercase and dotted, as spec 2's example `fin-pol-004.s4` is, and is what a node's `fundamento` names.
- `cita` is the clause exactly as spec 1 writes it, quoted, prefixed with the standard and its year; it is what the debt's command lists, so it is the only field that contains the string `ISO`.
- `funda` says, in English and without the string `ISO`, what spec 1 says the clause founds. Until spec 2 writes the tree, this field is the only permanent place the mapping from stage to clause lives.

## Review Focus

1. **A permanent page that cites a spec.** Spec 1 writes the new rule's tier as "*No gate holds this* until spec 4's grants do"; copied literally, it breaks "a permanent page never cites one". Task 3 writes `*No gate holds this.*` only; Task 5's grep catches any `spec [0-9]`, `pending-` or `superpowers` in a permanent page.
2. **`grep -o 'ISO[^"]*'` listing something that is not a clause.** If any `id` or `funda` contains `ISO`, the debt's command prints noise. Task 2's Step 3 compares the command's line count with the entry count.
3. **The sentence inserted in the wrong place.** "Gains one sentence after its first" means after "Advancing the simulated clock … for the new day.", the first sentence after the bold lead, because the new sentence's subject is the orchestrator that sentence starts (decided with the user). Task 3 Step 3 shows the paragraph after the edit.
4. **An invented clause.** ISO/IEC 42001 Annex A and ISO 22400-2 have no clause number in spec 1, and the entries carry none; the debt says so. Task 2's Step 3 reads every `cita` against spec 1's tables.
5. **"The decision tree" and "the kernel" used before they are defined.** The root's opening paragraph is the router's vocabulary (`docs_guide.md` §3), so Task 3 Step 2 defines both there in one clause each, before the sentence and the rules that use them. The plans of specs 2 and 4 write the detail on `packages/agents/AGENTS.md` and on the kernel's pages and do not restate the definition; Task 5's end-to-end read confirms each definition appears once.

---

### Task 1: Rename the spec now that its plan exists

**Files:**
- Rename: `docs/superpowers/2026-10-03-normative-foundations-pending-1.md` → `docs/superpowers/2026-10-03-normative-foundations.md`

**Interfaces:**
- Consumes: this plan, at `docs/superpowers/2026-10-03-normative-foundations-plan.md`.
- Produces: the spec at its final path, which the plan's header names.

`docs_guide.md` §3: "a spec written ahead of its plan carries a `-pending-N` suffix until the plan exists". The other specs name spec 1 as "spec 1, `normative-foundations`", never by path, so nothing else changes.

- [ ] **Step 1: Confirm nothing cites the old path**

Run: `grep -rn "normative-foundations-pending-1" --include='*.md' . | grep -v node_modules`
Expected: only lines of this plan.

- [ ] **Step 2: Rename**

Run: `git mv docs/superpowers/2026-10-03-normative-foundations-pending-1.md docs/superpowers/2026-10-03-normative-foundations.md`

- [ ] **Step 3: Update the spec's status line**

In `docs/superpowers/2026-10-03-normative-foundations.md`, replace

```
**Status:** pending its plan. **Series:**
```

with

```
**Status:** planned in `2026-10-03-normative-foundations-plan.md`. **Series:**
```

- [ ] **Step 4: Point this plan's header at the new path**

In this plan's `**Spec:**` line, replace the whole line with:

```
**Spec:** `docs/superpowers/2026-10-03-normative-foundations.md`. Read it whole before Task 2. The other five specs in `docs/superpowers/` are not planned here; Tasks 2 and 3 name the points where they constrain this plan.
```

- [ ] **Step 5: Verify**

Run: `git status --short`
Expected: `R  docs/superpowers/2026-10-03-normative-foundations-pending-1.md -> docs/superpowers/2026-10-03-normative-foundations.md` plus the plan and `docs/superpowers/2026-10-03-decision-tree-pending-2.md`, whose `explicar.misma_causa` row now names the registry id `iso9001.10.2.1.b.3` instead of a citation. Nothing else.

- [ ] **Step 6: Ask the user, then commit**

```bash
git add docs/superpowers/
git commit -q -F - <<'MSG'
Plan the normative foundations and rename their spec, and make spec 2 cite the registry by id

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 2: Create the registry of `fundamentos`

**Files:**
- Create: `packages/agents/arbol/fundamentos.yaml`

**Interfaces:**
- Consumes: spec 1's tables "The standards, and what each one founds", "The stages, mapped" and "The laws (level L0)".
- Produces: the file Task 3's rule links and Task 4's command reads. Spec 2's node field `fundamento` names an `id` of this file.

- [ ] **Step 1: Confirm the directory is empty and nothing writes there**

Run: `ls packages/agents/arbol 2>&1; grep -rn "arbol" --include='*.py' --include='*.ts' . | grep -v node_modules`
Expected: `No such file or directory`, and no grep hit. A hit means a generator writes there; stop and read `GENERATED.md`.

- [ ] **Step 2: Write the file**

Exactly this content, no comments:

```yaml
fundamentos:
  - id: iso31000.6.4.2
    cita: "ISO 31000:2018 §6.4.2"
    funda: "stage detectar: risk identification"
  - id: iso31000.6.4.3
    cita: "ISO 31000:2018 §6.4.3"
    funda: "stage explicar: risk analysis; the law that not enough evidence is a complete answer"
  - id: iso31000.6.4.4
    cita: "ISO 31000:2018 §6.4.4"
    funda: "stage proponer: risk evaluation"
  - id: iso31000.6.5.2
    cita: "ISO 31000:2018 §6.5.2"
    funda: "stage proponer: selection of treatment options"
  - id: iso31000.6.5.3
    cita: "ISO 31000:2018 §6.5.3"
    funda: "stages aprobar and ejecutar: treatment plans and their implementation"
  - id: iso31000.6.6
    cita: "ISO 31000:2018 §6.6"
    funda: "stages cerrar and medir: monitoring and review"
  - id: iso31000.6.7
    cita: "ISO 31000:2018 §6.7"
    funda: "stage cerrar: recording and reporting; the law that every step lands in the bitácora"
  - id: iso9001.7.5
    cita: "ISO 9001:2015 §7.5"
    funda: "the law that every figure comes from a logged query"
  - id: iso9001.9.1.1
    cita: "ISO 9001:2015 §9.1.1"
    funda: "stage medir: what is monitored and measured, how and when; the KPI kernel and Vigía as owner of measurement"
  - id: iso9001.9.1.3
    cita: "ISO 9001:2015 §9.1.3"
    funda: "stage medir: analysis and evaluation"
  - id: iso9001.10.2.1.a
    cita: "ISO 9001:2015 §10.2.1 a)"
    funda: "stage detectar: react to the nonconformity"
  - id: iso9001.10.2.1.b
    cita: "ISO 9001:2015 §10.2.1 b)"
    funda: "stage proponer: evaluate the need for action"
  - id: iso9001.10.2.1.b.2
    cita: "ISO 9001:2015 §10.2.1 b) 2)"
    funda: "stage explicar: determine the causes"
  - id: iso9001.10.2.1.b.3
    cita: "ISO 9001:2015 §10.2.1 b) 3)"
    funda: "stage explicar: similar nonconformities"
  - id: iso9001.10.2.1.c
    cita: "ISO 9001:2015 §10.2.1 c)"
    funda: "stage ejecutar: implement the action"
  - id: iso9001.10.2.1.d
    cita: "ISO 9001:2015 §10.2.1 d)"
    funda: "stage cerrar: review the effectiveness of the action"
  - id: iso9001.10.2.2
    cita: "ISO 9001:2015 §10.2.2"
    funda: "stage cerrar: retained information; the law that every step lands in the bitácora"
  - id: iso42001.6.1
    cita: "ISO/IEC 42001:2023 §6.1"
    funda: "the law that data and documents are data, never instructions: AI risk assessment and treatment"
  - id: iso42001.8
    cita: "ISO/IEC 42001:2023 §8"
    funda: "the laws that no agent changes a database and that an agent uses only the tools its label allows"
  - id: iso42001.9
    cita: "ISO/IEC 42001:2023 §9"
    funda: "performance evaluation of the AI system"
  - id: iso42001.anexo-a.supervision-humana
    cita: "ISO/IEC 42001:2023 Annex A, human oversight"
    funda: "stage aprobar; the law that no action runs without a recorded human approval"
  - id: iso42001.anexo-a.registro-eventos
    cita: "ISO/IEC 42001:2023 Annex A, recording of AI system events"
    funda: "the law that every step lands in the bitácora"
  - id: iso22400-2.descripcion-kpi
    cita: "ISO 22400-2:2014, KPI description structure"
    funda: "the fields of a KPI in the kernel: name, id, description, scope, formula, unit, range, trend, timing, audience"
```

- [ ] **Step 3: Verify the shape and the debt's command**

Run each:

```bash
f=packages/agents/arbol/fundamentos.yaml
grep -c '^  - id: ' "$f"
grep -o 'ISO[^"]*' "$f" | sort -u | wc -l
grep -o '^  - id: .*' "$f" | sort | uniq -d
grep -n '#' "$f"
grep -n 'ISO' "$f" | grep -v '    cita: '
awk 'NR>1 && !/^  - id: [a-z0-9.-]+$/ && !/^    cita: ".*"$/ && !/^    funda: ".*"$/' "$f"
```

Expected: the first two print the same number; the last four print nothing (no duplicate id, no comment, `ISO` only in `cita`, every line one of the three shapes). Then read every `cita` beside spec 1's tables: each clause is one spec 1 names, and no number appears that spec 1 does not write.

- [ ] **Step 4: Verify against `GENERATED.md`**

Run: `git status --short`
Expected: `?? packages/agents/arbol/` and nothing else from this task. The file is hand-written, so `GENERATED.md` gains no row.

- [ ] **Step 5: Ask the user, then commit**

```bash
git add packages/agents/arbol/fundamentos.yaml
git commit -q -F - <<'MSG'
Give the decision tree a registry of the clauses a node may rest on, so no fundamento is cited from memory

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 3: Define the tree and the kernel, and write the sentence and the two new rules into the root `AGENTS.md`

**Files:**
- Modify: `AGENTS.md` (`CLAUDE.md` is a symlink to it; never edit `CLAUDE.md` as a separate file)

**Interfaces:**
- Consumes: `packages/agents/arbol/fundamentos.yaml` from Task 2, which the new rule links.
- Produces: the root's definitions of **decision tree** and **kernel**, which the plans of specs 2 and 4 build on and do not restate; the rule "No agent changes a database", which the plans of specs 2 to 6 obey and the plan of spec 4 later gives a gate.

- [ ] **Step 1: Confirm the anchors exist once each**

Run:

```bash
grep -c 'for the new day. `Vigía` reads the views' AGENTS.md
grep -c '^- \*\*No action without a recorded human approval\*\*' AGENTS.md
grep -c '^\*\*Still undecided, and owned by no page yet:\*\*' AGENTS.md
grep -c 'append-only log of every decision. The challenge in full is' AGENTS.md
```

Expected: `1` four times.

- [ ] **Step 2: Define the decision tree and the kernel in the opening paragraph**

Replace

```
approval); the **`bitácora`** is the append-only log of every decision. The challenge in full is
```

with

```
approval); the **`bitácora`** is the append-only log of every decision; the **decision tree** is
the data in `packages/agents/arbol/` the orchestrator walks, atomic rules whose leaves are an
agent's decisions; the **kernel** is the closed language every KPI is defined in and compiled to
SQL from, the one place an agent reads a business measure. The challenge in full is
```

Leave the rest of the paragraph, from "The challenge in full is", as it is. The definitions link no page: `packages/agents/AGENTS.md` and the kernel's pages do not describe either yet, and the root's other terms (**view**, **simulated clock**) are defined the same way.

- [ ] **Step 3: Insert the sentence in "How the parts connect"**

Replace

```
orchestrator in `packages/agents` for the new day. `Vigía` reads the views through
```

with

```
orchestrator in `packages/agents` for the new day. The orchestrator walks the decision tree of
`packages/agents`, whose stages follow ISO 31000 and ISO 9001 §10.2, and each agent reads its
measures from the kernel. `Vigía` reads the views through
```

The paragraph then opens: "**An alert walks the chain like this.** Advancing the simulated clock in `apps/api` starts the orchestrator in `packages/agents` for the new day. The orchestrator walks the decision tree …". Leave line wrapping of the rest of the paragraph as it is.

- [ ] **Step 4: Add the sibling rule and the registry rule in "Rules every change follows"**

Replace

```
- **No action without a recorded human approval**, and every action is a draft or a sandbox effect.
  *No gate holds this.*
```

with

```
- **No action without a recorded human approval**, and every action is a draft or a sandbox effect.
  *No gate holds this.*
- **No agent changes a database**: not the dataset, not the kernel's catalogue, not the API's
  state. An agent returns outputs; `apps/api` persists its own. *No gate holds this.*
- **A node of the decision tree or a KPI rests on one entry of the registry**,
  [`packages/agents/arbol/fundamentos.yaml`](./packages/agents/arbol/fundamentos.yaml); a standard
  founds structure, a policy founds a threshold, and only a person adds to the registry.
  *No gate holds this.*
```

Two departures from spec 1's wording, each for a rule of this tree: the tier is `*No gate holds this.*` without "until spec 4's grants do", because a permanent page never cites a spec (the plan of spec 4 rewrites the tier when its grants exist); and the registry rule links the file, because "the registry" is defined on no other permanent page yet and the router names a domain word once and links the page that defines it (`docs_guide.md` §3).

- [ ] **Step 5: Leave "Still undecided" as it is**

Spec 1: "nothing removed; the tree and the kernel settle none of the three open questions." Run: `git diff AGENTS.md | grep -n '^[-+].*Still undecided'`
Expected: no output.

- [ ] **Step 6: Verify links and status**

Run the link check from the root `AGENTS.md`, "Verification only a person runs", item 5:

```bash
for f in $(git ls-files -co --exclude-standard '*.md'); do
  awk '/^[[:space:]]*```/{c=!c;next} !c' "$f" | grep -o '](\.[^)#]*' | sed 's/](//' |
    while read -r l; do [ -e "$(dirname "$f")/$l" ] || echo "$f -> $l"; done
done
```

Expected: no output. Then `git status --short`: expected ` M AGENTS.md` and nothing else from this task (`CLAUDE.md` does not appear: it is a symlink).

- [ ] **Step 7: Read the root end to end**

Read `AGENTS.md` whole. Check: present tense in the four new passages; `grep -c '\*\*decision tree\*\*' AGENTS.md` and `grep -c '\*\*kernel\*\*' AGENTS.md` each print `1`; no spec, plan or `pending` cited; "No agent changes a database" is stated nowhere else in the root (`grep -n 'changes a database' AGENTS.md` prints one line); the new sentence does not restate the stage table.

- [ ] **Step 8: Ask the user, then commit**

```bash
git add AGENTS.md
git commit -q -F - <<'MSG'
Define the decision tree and the kernel, bind every change to the registry, and forbid an agent to change a database, so its effects stay where approval and the `bitácora` see them

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 4: File the debt of the unverified clauses in `DOUBTS.md`

**Files:**
- Modify: `DOUBTS.md`, section "Filed debts"

**Interfaces:**
- Consumes: `packages/agents/arbol/fundamentos.yaml` from Task 2; its `cita` field is what the command lists.
- Produces: the record a person pays before the first node of the tree cites an entry.

Why a paragraph and not a higher place in `DOUBTS.md`'s order: it cannot be paid (the texts are licensed and not in the tree); no gate or test exists that could hold it; a level page would be `packages/agents/AGENTS.md`, whose registry section spec 2 writes; and YAML carries no comment.

- [ ] **Step 1: Append the debt at the end of "Filed debts"**

After the last line of the file (the brief's re-derive command), add one blank line and:

```
**The clauses the registry cites are unverified.**
[`packages/agents/arbol/fundamentos.yaml`](./packages/agents/arbol/fundamentos.yaml) cites clauses
of ISO 31000, ISO 9001, ISO/IEC 42001 and ISO 22400-2, and the texts of those standards are
licensed and not in the tree, so no reader can check that a clause says what its entry claims. The
entries for ISO/IEC 42001 Annex A and for ISO 22400-2 name no clause number at all. It costs a
`fundamento` that cites the wrong clause, which founds nothing. It is paid when a person with
access to the texts confirms every entry, before the first node of the decision tree cites one.
Re-derive it with `grep -o 'ISO[^"]*' packages/agents/arbol/fundamentos.yaml | sort -u`.
```

The sentence enumerating the standards is admitted by the count rule: it names what it lists, and it lists standards, not entries.

- [ ] **Step 2: Run the command the debt hands over**

Run: `grep -o 'ISO[^"]*' packages/agents/arbol/fundamentos.yaml | sort -u`
Expected: one line per `cita`, each starting `ISO`, and no `No such file` error.

- [ ] **Step 3: Verify links, status and the read**

Run the link check of Task 3 Step 6: no output. `git status --short`: ` M DOUBTS.md` only. Read `DOUBTS.md` whole: the new entry has the shape of the one above it (what is wrong, what it costs, when it is paid, the command), is in the present tense and cites no spec.

- [ ] **Step 4: Ask the user, then commit**

```bash
git add DOUBTS.md
git commit -q -F - <<'MSG'
File the unverified ISO clauses as a debt, because a fundamento that cites the wrong clause founds nothing

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
```

---

### Task 5: Verify the whole change against the root and against the spec's acceptance

**Files:**
- Read only: `AGENTS.md`, `DOUBTS.md`, `packages/agents/arbol/fundamentos.yaml`, `apps/api/AGENTS.md`, `docs/superpowers/2026-10-03-normative-foundations.md`

- [ ] **Step 1: No permanent page cites a spec or a plan**

Run: `git grep -nE 'spec [0-9]|pending-[0-9]|docs/superpowers|normative-foundations' -- ':!docs/superpowers'`
Expected: one hit only, the root rule "Specs and plans are dated, `docs/superpowers/YYYY-MM-DD-<name>.md`", which names the convention and cites no spec. Any other hit is a citation to remove.

- [ ] **Step 2: The checklist of "Pages this spec changes" is done**

| Spec row | Done by | Check |
|---|---|---|
| `AGENTS.md`, sentence after the first of "An alert walks the chain like this." | Task 3 Step 3 | `grep -c 'walks the decision tree' AGENTS.md` prints `1` |
| `AGENTS.md`, sibling "No agent changes a database" | Task 3 Step 4 | `grep -c 'No agent changes a database' AGENTS.md` prints `1` |
| `AGENTS.md`, rule on the registry | Task 3 Step 4 | `grep -c 'rests on one entry of the registry' AGENTS.md` prints `1` |
| `AGENTS.md`, definitions of the decision tree and the kernel, the spec's first row | Task 3 Step 2 | `grep -c 'the \*\*kernel\*\* is the closed language' AGENTS.md` prints `1` |
| `AGENTS.md`, "Still undecided" unchanged | Task 3 Step 5 | `git log -p -1 --format= -- AGENTS.md | grep -c '^[-+].*Still undecided'` prints `0` |
| `DOUBTS.md`, the debt | Task 4 | `grep -c 'The clauses the registry cites are unverified' DOUBTS.md` prints `1` |

- [ ] **Step 3: The spec's acceptance on the lifecycle**

Read the transition table of `apps/api/AGENTS.md` and confirm each row maps to a stage of spec 1's table, and each agent has one:

| Transition | Stage |
|---|---|
| → `nueva` | `detectar` (`Vigía`) |
| `nueva` → `en análisis` | `detectar` (`Vigía` writes the title) |
| `en análisis` → `propuesta` | `explicar` (`Analista`), then `proponer` (`Estratega`) |
| `en análisis` → `unida` | `explicar` (`Analista` finds the same cause) |
| `propuesta` → `aprobada` or `rechazada` | `aprobar` (a person) |
| `aprobada` → `ejecutada` | `ejecutar` (`Ejecutor`), then `cerrar` (`apps/api`) |

A row of `apps/api/AGENTS.md` absent from this table is a gap in the spec: report it to the user, do not patch the spec silently. The other acceptance lines of spec 1 bind later specs and are checked by their plans.

- [ ] **Step 4: Run the root's person-only list, items 4 to 6**

Item 4: `git status --short` against `GENERATED.md`: after the commits, no output; before them, only the files of Tasks 1 to 4. Item 5: the link check prints nothing. Item 6: read `AGENTS.md`, `DOUBTS.md` and `fundamentos.yaml` end to end, for present tense and for a fact stated in two places.

- [ ] **Step 5: Report**

Tell the user which commits exist (`git log --oneline main..HEAD`), the output of Steps 1 and 4, and that the plans of specs 2 and 4 must build on the root's definitions of the decision tree and the kernel without restating them.
