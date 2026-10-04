import { posix } from 'node:path';
import { runGate, staleProblems, zeroScanProblems } from './gate.ts';
import { ROOT, codeSpans, ignored, proseLines, read, walk } from './tree.ts';

export const UNMARKED = new Map<string, string>([
  ['package-lock.json', 'npm install writes it whole from package.json, and JSON has no room for a banner'],
  ['apps/web/package-lock.json', 'npm install writes it whole from apps/web/package.json, and JSON has no room for a banner'],
  ['packages/agents/uv.lock', 'uv writes it whole from the pyproject.toml beside it and owns its format'],
  ['packages/tools/uv.lock', 'uv writes it whole from the pyproject.toml beside it and owns its format'],
  ['data/generator/csv/', 'the dataset generator writes one CSV per table, CSV has no room for a banner, and git ignores the directory'],
]);

export const WHOLE_FILE_NAMES = ['package-lock.json', 'uv.lock', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock'];

const BANNER = /(?:written|generated) by\s+`[^`]+`/i;

export function holds(root: string, files: string[], key: string): boolean {
  return key.endsWith('/') ? files.some((path) => path.startsWith(key)) || ignored(root, key) : files.includes(key);
}

export function namedIn(root: string, files: string[]): Set<string> {
  if (!files.includes('GENERATED.md')) return new Set();
  return new Set(proseLines(read(root, 'GENERATED.md')).flatMap(codeSpans));
}

export function problems(root = ROOT, unmarked = UNMARKED): string[] {
  const files = walk(root);
  const marked = files.filter((path) => posix.basename(path).includes('.generated.'));
  const whole = files.filter((path) => WHOLE_FILE_NAMES.includes(posix.basename(path)));
  const named = namedIn(root, files);
  return [
    ...(files.includes('GENERATED.md') ? [] : ['GENERATED.md is missing; it says which half of each file is a person\'s']),
    ...zeroScanProblems('generated files', marked.length + whole.length),
    ...staleProblems('UNMARKED', unmarked, (key) => holds(root, files, key)),
    ...marked
      .filter((path) => !BANNER.test(read(root, path).split('\n').slice(0, 3).join('\n')))
      .map((path) => `${path} is named generated and its first lines carry no banner naming the command that writes it`),
    ...whole
      .filter((path) => !unmarked.has(path))
      .map((path) => `${path} is written whole by a tool, is not named .generated. and is missing from UNMARKED`),
    ...[...marked, ...unmarked.keys()]
      .filter((path) => !named.has(path))
      .map((path) => `${path} is written by a generator and GENERATED.md does not name it`),
  ];
}

if (import.meta.main) runGate(() => problems());
