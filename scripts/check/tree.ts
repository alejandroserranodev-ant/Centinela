import { execFileSync } from 'node:child_process';
import { lstatSync, readFileSync } from 'node:fs';
import { dirname, join, posix, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

export const FOREIGN = new Set([
  '.git',
  '.claude',
  '.superpowers',
  'node_modules',
  '.venv',
  'dist',
  '__pycache__',
  '.pytest_cache',
]);

export const DATED_PROCESS_DOCUMENTS = 'docs/superpowers/';

export function present(root: string, path: string): boolean {
  try {
    lstatSync(join(root, path));
    return true;
  } catch {
    return false;
  }
}

export function walk(root: string): string[] {
  const listed = execFileSync('git', ['ls-files', '-co', '--exclude-standard', '-z'], {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 1 << 28,
  });
  return [...new Set(listed.split('\0'))]
    .filter((path) => path !== '')
    .filter((path) => !path.split('/').some((segment) => FOREIGN.has(segment)))
    .filter((path) => present(root, path))
    .sort();
}

export function ignored(root: string, path: string): boolean {
  try {
    execFileSync('git', ['check-ignore', '-q', '--no-index', path], { cwd: root, stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

export function read(root: string, path: string): string {
  return readFileSync(join(root, path), 'utf8');
}

export function isSymlink(root: string, path: string): boolean {
  return lstatSync(join(root, path)).isSymbolicLink();
}

export function directories(files: string[]): Set<string> {
  const found = new Set<string>();
  for (const file of files) {
    let dir = posix.dirname(file);
    while (dir !== '.' && !found.has(dir)) {
      found.add(dir);
      dir = posix.dirname(dir);
    }
  }
  return found;
}

export function documents(files: string[]): string[] {
  return files.filter((path) => path.endsWith('.md'));
}

export function isDatedProcessDocument(path: string): boolean {
  return path.startsWith(DATED_PROCESS_DOCUMENTS);
}

export function proseLines(text: string): string[] {
  let fenced = false;
  return text.split('\n').map((line) => {
    if (/^\s*(```|~~~)/.test(line)) {
      fenced = !fenced;
      return '';
    }
    return fenced ? '' : line;
  });
}

export function fencedLines(text: string): string[] {
  let fenced = false;
  return text.split('\n').map((line) => {
    if (/^\s*(```|~~~)/.test(line)) {
      fenced = !fenced;
      return '';
    }
    return fenced ? line : '';
  });
}

export function paragraphs(lines: string[]): string[][] {
  const found: string[][] = [];
  let current: string[] = [];
  for (const line of lines) {
    if (line.trim() === '') {
      if (current.length > 0) found.push(current);
      current = [];
    } else {
      current.push(line);
    }
  }
  if (current.length > 0) found.push(current);
  return found;
}

export function codeSpans(line: string): string[] {
  return [...line.matchAll(/`([^`]+)`/g)].map((match) => match[1].trim());
}

export function links(line: string): string[] {
  const withoutSpans = line.replace(/`[^`]*`/g, '');
  return [...withoutSpans.matchAll(/\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g)].map((match) => match[1]);
}

export function isExternal(target: string): boolean {
  return /^[a-z][a-z0-9+.-]*:/i.test(target);
}

export function slug(heading: string): string {
  return heading
    .trim()
    .toLowerCase()
    .replace(/`/g, '')
    .replace(/[^\p{L}\p{N}\s_-]/gu, '')
    .replace(/\s/g, '-');
}

export function anchors(text: string): Set<string> {
  const counts = new Map<string, number>();
  const found = new Set<string>();
  for (const line of proseLines(text)) {
    const heading = /^#{1,6}\s+(.*?)\s*#*\s*$/.exec(line);
    if (!heading) continue;
    const base = slug(heading[1]);
    const seen = counts.get(base) ?? 0;
    found.add(seen === 0 ? base : `${base}-${seen}`);
    counts.set(base, seen + 1);
  }
  return found;
}

export const MANIFESTS = ['package.json', 'pyproject.toml'];

export function manifestDirectories(files: string[], kind?: string): string[] {
  return files
    .filter((path) => (kind ? posix.basename(path) === kind : MANIFESTS.includes(posix.basename(path))))
    .map((path) => posix.dirname(path));
}

export function nearestManifestDirectory(files: string[], path: string, kind?: string): string | undefined {
  const owners = new Set(manifestDirectories(files, kind));
  let dir = posix.dirname(path);
  while (true) {
    if (owners.has(dir)) return dir;
    if (dir === '.') return undefined;
    dir = posix.dirname(dir);
  }
}

export function resolveFrom(base: string, target: string): string {
  return posix.normalize(posix.join(base, target)).replace(/\/$/, '');
}
