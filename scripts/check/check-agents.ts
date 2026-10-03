import { readlinkSync } from 'node:fs';
import { join, posix } from 'node:path';
import { runGate, staleProblems, zeroScanProblems } from './gate.ts';
import {
  ROOT,
  documents,
  isExternal,
  isSymlink,
  links,
  manifestDirectories,
  proseLines,
  read,
  resolveFrom,
  walk,
} from './tree.ts';

export const SURVIVORS = new Map<string, string>([
  ['README.md', 'what a forge renders on the repository page; it points at the router and carries no rule'],
]);

export function reachable(root: string, files: string[]): Set<string> {
  const known = new Set(documents(files));
  const seen = new Set<string>();
  const queue = known.has('AGENTS.md') ? ['AGENTS.md'] : [];
  while (queue.length > 0) {
    const page = queue.shift() as string;
    if (seen.has(page)) continue;
    seen.add(page);
    for (const line of proseLines(read(root, page))) {
      for (const target of links(line)) {
        if (isExternal(target)) continue;
        const path = target.split('#')[0];
        if (path === '') continue;
        const resolved = resolveFrom(posix.dirname(page), path);
        if (known.has(resolved) && !seen.has(resolved)) queue.push(resolved);
      }
    }
  }
  return seen;
}

export function levelProblems(root: string, files: string[]): string[] {
  const linked = reachable(root, files);
  return files
    .filter((path) => posix.basename(path) === 'AGENTS.md')
    .filter((path) => !linked.has(path))
    .map((path) => `${path} is a level no chain of links from AGENTS.md reaches`);
}

export function readmeProblems(files: string[], survivors = SURVIVORS): string[] {
  return files
    .filter((path) => posix.basename(path).toLowerCase() === 'readme.md')
    .filter((path) => !survivors.has(path))
    .map((path) => `${path} is a README outside SURVIVORS; README.md at the root is the only one`);
}

export function symlinkProblems(root: string, files: string[]): string[] {
  if (!files.includes('CLAUDE.md')) return ['CLAUDE.md is missing; it is a symlink to AGENTS.md'];
  if (!isSymlink(root, 'CLAUDE.md') || readlinkSync(join(root, 'CLAUDE.md')) !== 'AGENTS.md') {
    return ['CLAUDE.md is not a symlink to AGENTS.md'];
  }
  return [];
}

export function manifestProblems(files: string[]): string[] {
  const pages = new Set(files.filter((path) => posix.basename(path) === 'AGENTS.md').map((path) => posix.dirname(path)));
  return manifestDirectories(files)
    .filter((dir) => !pages.has(dir))
    .map((dir) => `${dir === '.' ? 'the root' : dir} holds a manifest and no AGENTS.md beside it to name its commands`);
}

export function problems(root = ROOT, survivors = SURVIVORS): string[] {
  const files = walk(root);
  const levels = files.filter((path) => posix.basename(path) === 'AGENTS.md');
  return [
    ...zeroScanProblems('AGENTS.md pages', levels.length),
    ...staleProblems('SURVIVORS', survivors, (key) => files.includes(key)),
    ...levelProblems(root, files),
    ...readmeProblems(files, survivors),
    ...symlinkProblems(root, files),
    ...manifestProblems(files),
  ];
}

if (import.meta.main) runGate(() => problems());
