import { posix } from 'node:path';
import { runGate, staleProblems, zeroScanProblems } from './gate.ts';
import { ROOT, isExternal, links, proseLines, read, resolveFrom, walk } from './tree.ts';

export const ROUTER = 'AGENTS.md';
export const STALE_UNDER = 0.15;
export const REASON_CAP = 160;

export type Budget = [number, string];

export const ENTRIES = new Map<string, Budget>([
  [ROUTER, [13000, 'the router carries the vocabulary, the question table, the rules and the checks every change asks']],
]);

export const ROUTES = new Map<string, Budget>([
  ["the chat answered, refused or stayed silent when it should not have", [62500, "the chat's agent and its subtree are stated on the agents page and the tree's page"]],
  ["an alert is missing, wrong, duplicated or fires on the wrong day", [87000, "the agents, the tree and the clock are the three places a detection is decided"]],
  ["a number on screen disagrees with SQL", [43923, "a screen's figure comes from the fetch client or from what the API serves, and both pages say which"]],
  ["a number in an agent's answer or an alert disagrees with SQL", [47000, "a figure comes from the compiler and from the base KPI it compiles"]],
  ["something happened without approval, or the log is missing a step", [25137, "the decision checks, the in-process agents and the bitácora are stated on one page"]],
  ["a screen renders or behaves wrong", [19286, "the screens' decisions and their person-run check are one page"]],
  ["`npm run check` failed, or I am adding a gate", [6000, "one page names every gate and the maps that excuse a case"]],
  ["what the challenge requires, what the jury tests, what is out of scope", [8500, "the brief's requirements are read on one page"]],
  ["a table, a CSV, a threshold, a policy document, the database setup, the generator", [24000, "one page owns the dataset, its setup and its generator"]],
  ["a KPI's definition, the kernel's language, a refusal by a guard", [47000, "the language is data's and the compiler is the tools', so both are read"]],
  ["a node, a leaf, a level, a stage or the registry of the decision tree", [23000, "the tree's own page states every rule a node is written by"]],
  ["an agent, the orchestrator, which model a step uses", [40000, "one page holds the agents, the orchestrator and the model providers"]],
  ["the instructions a model step loads, its skill", [6500, "the rules a skill is written by fit one short page"]],
  ["a tool an agent calls: SQL, policy search, impact, an action", [23500, "one page holds every tool, built or decided"]],
  ["an endpoint, the clock, the alert lifecycle, roles, the `bitácora`", [25137, "the API's page holds the clock, the lifecycle and the roles"]],
  ["a screen, a component, the Arena skin", [19286, "the screens' decisions and the skin's rules are one page"]],
  ["an evaluation case, or proving nothing regressed", [9500, "the evaluation page lists the cases and what runs them"]],
  ["adding a metric that raises alerts, or a KPI that is evidence", [45500, "a metric is defined in the kernel first and wired into the tree second"]],
  ["adding a node, an end, an orchestrator write, an agent decision or an action type", [23000, "the tree's checklists sit on the tree's own page"]],
  ["adding a skill", [6500, "the checklist for a skill sits on the skills page"]],
  ["adding a tool or a guard", [23500, "the checklists for a tool and a guard sit on the tools page"]],
  ["adding an endpoint", [25137, "the endpoint table and its rule sit on the API's page"]],
  ["adding a screen", [19286, "the checklist for a screen sits on the web page"]],
  ["adding an evaluation case", [9500, "the checklist for a case sits on the evaluation page"]],
  ["running the database, the API and the web together on my machine", [3213, "the local run across levels is one short page"]],
  ["which model provider the agents call, its key or its variables", [3500, "the variables the providers read are one short page"]],
  ["the guide a developer reads in Docmost, its compose, or one of its chapters", [5500, "the guide's build and its compose are one page"]],
  ["how a page, a spec or a plan is written", [38000, "the practice every page follows is one reference, read whole"]],
  ["whether the file in front of me is mine to edit", [4750, "which half of a file is a person's is one companion page"]],
  ["I am about to write down that something is wrong", [4500, "what counts as a debt and where it goes is one companion page"]],
]);

export type Row = { question: string; stops: string[] };

export function rows(text: string, page = ROUTER): Row[] {
  const found: Row[] = [];
  let inTable = false;
  for (const line of proseLines(text)) {
    if (/^\|\s*I am here because\s*\|/.test(line)) {
      inTable = true;
      continue;
    }
    if (!inTable) continue;
    if (!line.trim().startsWith('|')) break;
    if (/^\|[\s|:-]+\|$/.test(line.trim())) continue;
    const cells = line.split(/(?<!\\)\|/).slice(1, -1);
    const stops = links(cells.slice(1).join('|'))
      .filter((target) => !isExternal(target))
      .map((target) => resolveFrom(posix.dirname(page), target.split('#')[0]));
    found.push({ question: cells[0].trim(), stops: [...new Set(stops)] });
  }
  return found;
}

export function size(root: string, path: string): number {
  return [...read(root, path)].length;
}

export function budgetProblems(name: string, cost: number, budget: Budget): string[] {
  const [limit, reason] = budget;
  const found: string[] = [];
  if (cost > limit) found.push(`${name} costs ${cost} characters, over its budget of ${limit}`);
  if (cost < limit * (1 - STALE_UNDER)) found.push(`${name} costs ${cost} characters, more than 15% under its budget of ${limit}, which is stale`);
  if (/\d/.test(reason)) found.push(`${name}'s reason names a figure; a reason says why the budget is right today`);
  if (/\b(raised|lowered)\b/i.test(reason)) found.push(`${name}'s reason tells its history; the commit that moved it carries that`);
  if ([...reason].length > REASON_CAP) found.push(`${name}'s reason passes ${REASON_CAP} characters`);
  return found;
}

export function problems(root = ROOT, entries = ENTRIES, routes = ROUTES): string[] {
  const files = walk(root);
  if (!files.includes(ROUTER)) return [`${ROUTER} is missing, so no route can be measured`];
  const table = rows(read(root, ROUTER));
  const questions = new Set(table.map((row) => row.question));
  return [
    ...zeroScanProblems('router rows', table.length),
    ...staleProblems('ENTRIES', entries, (key) => files.includes(key)),
    ...staleProblems('ROUTES', routes, (key) => questions.has(key)),
    ...[...entries].flatMap(([path, budget]) => (files.includes(path) ? budgetProblems(path, size(root, path), budget) : [])),
    ...table.flatMap((row) => {
      const budget = routes.get(row.question);
      if (budget === undefined) return [`the router row "${row.question}" has no budget in ROUTES`];
      const missing = row.stops.filter((stop) => !files.includes(stop));
      if (missing.length > 0) return [`the router row "${row.question}" sends a reader to ${missing.join(', ')}, which is not a file`];
      const cost = row.stops.reduce((sum, stop) => sum + size(root, stop), 0);
      return budgetProblems(`the route "${row.question}"`, cost, budget);
    }),
  ];
}

if (import.meta.main) runGate(() => problems());
