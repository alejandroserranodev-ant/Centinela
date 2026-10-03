import { posix } from 'node:path';
import { runGate, staleProblems, zeroScanProblems } from './gate.ts';
import { ROOT, isExternal, links, proseLines, read, resolveFrom, walk } from './tree.ts';

export const ROUTER = 'AGENTS.md';
export const STALE_UNDER = 0.15;
export const REASON_CAP = 160;

export type Budget = [number, string];

export const ENTRIES = new Map<string, Budget>([
  [ROUTER, [11000, 'the router carries the vocabulary, the question table, the rules and the checks every change asks']],
]);

export const ROUTES = new Map<string, Budget>();

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
