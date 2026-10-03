import { posix } from 'node:path';
import { runGate, staleProblems, zeroScanProblems } from './gate.ts';
import {
  ROOT,
  codeSpans,
  documents,
  isDatedProcessDocument,
  isSymlink,
  manifestDirectories,
  nearestManifestDirectory,
  read,
  resolveFrom,
  walk,
} from './tree.ts';

export const EXEMPT_DOCUMENTS = new Map<string, string>([
  ['docs_guide.md', 'it describes Arena, another tree, whose commands run on Bun against manifests this tree does not hold'],
]);

export const EXEMPT = new Map<string, string>();

type Block = { commands: string[]; context: string };

export function blocks(text: string): Block[] {
  const found: Block[] = [];
  let prose: string[] = [];
  let fence: string[] | undefined;
  let previous = '';
  const closeProse = () => {
    if (prose.length === 0) return;
    const context = prose.join('\n');
    found.push({ commands: prose.flatMap(codeSpans), context });
    previous = context;
    prose = [];
  };
  for (const line of text.split('\n')) {
    if (/^\s*(```|~~~)/.test(line)) {
      if (fence === undefined) {
        closeProse();
        fence = [];
      } else {
        found.push({ commands: fence, context: previous });
        fence = undefined;
      }
      continue;
    }
    if (fence !== undefined) fence.push(line.trim().replace(/^\$\s+/, ''));
    else if (line.trim() === '') closeProse();
    else prose.push(line);
  }
  closeProse();
  return found;
}

export function segments(command: string): { dir?: string; words: string[] }[] {
  let dir: string | undefined;
  const found: { dir?: string; words: string[] }[] = [];
  for (const part of command.split(/&&|;|\|\|?/)) {
    const words = part.trim().split(/\s+/).filter(Boolean);
    while (words.length > 0 && /^[A-Z_][A-Z0-9_]*=/.test(words[0])) words.shift();
    if (words[0] === 'cd' && words[1]) {
      dir = words[1];
      continue;
    }
    if (words.length > 0) found.push({ dir, words });
  }
  return found;
}

type Ask = { kind: 'package.json' | 'pyproject.toml' | 'file'; what: string; holds: (dir: string) => boolean };

function scriptsOf(root: string, dir: string): Record<string, string> {
  try {
    return JSON.parse(read(root, posix.join(dir, 'package.json'))).scripts ?? {};
  } catch {
    return {};
  }
}

export function ask(root: string, files: string[], words: string[]): Ask | undefined {
  const known = new Set(files);
  const has = (dir: string, path: string) => known.has(posix.normalize(posix.join(dir, path)));
  const [head, second, third, fourth] = words;
  if ((head === 'python' || head === 'python3') && second?.endsWith('.py')) {
    return { kind: 'file', what: `script ${second}`, holds: (dir) => has(dir, second) };
  }
  if (head === 'npm') {
    const script = second === 'run' || second === 'run-script' ? third : second === 'test' || second === 'start' ? second : undefined;
    if (script === undefined || script.startsWith('-')) return undefined;
    return { kind: 'package.json', what: `npm script ${script}`, holds: (dir) => script in scriptsOf(root, dir) };
  }
  if (head !== 'uv' || second !== 'run' || third === undefined) return undefined;
  if (third === 'python' && fourth === '-m' && words[4]) {
    const module = words[4].replace(/\./g, '/');
    return {
      kind: 'pyproject.toml',
      what: `module ${words[4]}`,
      holds: (dir) => has(dir, `${module}.py`) || has(dir, `${module}/__init__.py`) || has(dir, `${module}/__main__.py`),
    };
  }
  const script = third === 'python' ? fourth : third;
  if (script?.endsWith('.py')) {
    return { kind: 'pyproject.toml', what: `script ${script}`, holds: (dir) => has(dir, script) };
  }
  if (third === 'python' || third.startsWith('-')) return undefined;
  const targets = words.slice(3).filter((word) => /\.py(?:::|$)/.test(word)).map((word) => word.split('::')[0]);
  return {
    kind: 'pyproject.toml',
    what: targets.length === 0 ? `tool ${third}` : `tool ${third} with ${targets.join(' ')}`,
    holds: (dir) => targets.every((target) => has(dir, target)) && new RegExp(`["']${third.replace(/[-_]/g, '[-_]')}(?:[\\s\\[<>=~!;"']|$)`, 'm').test(read(root, posix.join(dir, 'pyproject.toml'))),
  };
}

export function governing(files: string[], page: string, context: string, kind: string, dir?: string): string[] {
  const base = posix.dirname(page);
  if (kind === 'file') {
    return [...new Set(dir === undefined ? [base, '.'] : [resolveFrom(base, dir), resolveFrom('.', dir)])];
  }
  const owners = new Set(manifestDirectories(files, kind));
  if (dir !== undefined) {
    return [...new Set([resolveFrom(base, dir), resolveFrom('.', dir)])].filter((one) => owners.has(one));
  }
  const named = [...context.matchAll(/[\w.@-]+(?:\/[\w.@-]+)*\/?/g)]
    .map((match) => match[0].replace(/\/$/, ''))
    .flatMap((path) => [resolveFrom(base, path), resolveFrom('.', path)])
    .filter((one) => owners.has(one) && one !== '.');
  const nearest = nearestManifestDirectory(files, page, kind);
  return [...new Set([...named, ...(nearest === undefined ? [] : [nearest])])];
}

type Unresolved = { key: string; problem: string };

export function pageProblems(root: string, files: string[], page: string): Unresolved[] {
  const found: Unresolved[] = [];
  for (const block of blocks(read(root, page))) {
    for (const command of block.commands) {
      for (const segment of segments(command)) {
        const wanted = ask(root, files, segment.words);
        if (wanted === undefined) continue;
        const dirs = governing(files, page, block.context, wanted.kind, segment.dir);
        if (dirs.some(wanted.holds)) continue;
        const where =
          wanted.kind === 'file'
            ? `neither ${dirs.join(' nor ')} holds it`
            : dirs.length === 0
              ? `no ${wanted.kind} governs the page`
              : `${dirs.map((dir) => posix.join(dir, wanted.kind)).join(' or ')} declares no ${wanted.what}`;
        found.push({ key: `${page} → ${command}`, problem: `${page}: \`${command}\` runs ${wanted.what}, and ${where}` });
      }
    }
  }
  return found;
}

export function problems(root = ROOT, exempt = EXEMPT, exemptDocuments = EXEMPT_DOCUMENTS): string[] {
  const files = walk(root);
  const pages = documents(files).filter(
    (page) => !isDatedProcessDocument(page) && !exemptDocuments.has(page) && !isSymlink(root, page),
  );
  const found = pages.flatMap((page) => pageProblems(root, files, page));
  const keys = new Set(found.map((one) => one.key));
  return [
    ...zeroScanProblems('documents', pages.length),
    ...staleProblems('EXEMPT_DOCUMENTS', exemptDocuments, (key) => files.includes(key)),
    ...staleProblems('EXEMPT', exempt, (key) => keys.has(key)),
    ...found.filter((one) => !exempt.has(one.key)).map((one) => one.problem),
  ];
}

if (import.meta.main) runGate(() => problems());
