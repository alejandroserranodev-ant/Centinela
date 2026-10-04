import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { join, posix } from 'node:path';
import { CannotRun, runGate, staleProblems, zeroScanProblems } from './gate.ts';
import { ROOT, documents, isDatedProcessDocument, isSymlink, proseLines, read, walk } from './tree.ts';

export const DOCUMENT_CAP = 60000;
export const CELL_CAP = 2000;
export const HEADER_CAP = 10;

export const ALLOWANCES = new Map<string, [number, string]>();

export const VENDORED = new Map<string, string>([
  ['data/sql/01_esquema.sql', 'the kit delivers the schema with its comments, and the root rule keeps kit files as delivered'],
  ['data/sql/02_carga.sql', 'the kit delivers the load script with its comments, and the root rule keeps kit files as delivered'],
  ['data/sql/03_capa_semantica.sql', 'the kit delivers the semantic layer with its comments, and the root rule keeps kit files as delivered'],
  ['data/generator/generar_dataset.py', 'the kit delivers the generator with its comments, and the root rule keeps kit files as delivered'],
]);

const SOURCE = /\.(py|ts|tsx|js|mjs|sql)$/;

export function isScript(path: string, text: string): boolean {
  const name = posix.basename(path);
  return (
    path.endsWith('.sql') ||
    path.split('/').some((segment) => segment === 'tests' || segment === 'scripts') ||
    /^test_.*\.py$|^conftest\.py$|\.test\.tsx?$/.test(name) ||
    /if __name__ == ["']__main__["']|import\.meta\.main/.test(text)
  );
}

export function sources(files: string[], vendored = VENDORED): string[] {
  return files.filter((path) => SOURCE.test(path) && !path.includes('.generated.') && !vendored.has(path));
}

type Comment = { line: number; lines: number };

const PYTHON_COMMENTS = `
import io, json, sys, tokenize
found = {}
for path in json.load(sys.stdin):
    rows = []
    with open(path, "rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type == tokenize.COMMENT and not (token.start[0] == 1 and token.string.startswith("#!")):
                rows.append(token.start[0])
    found[path] = rows
print(json.dumps(found))
`;

export function pythonComments(root: string, paths: string[]): Map<string, Comment[]> {
  if (paths.length === 0) return new Map();
  let answer: string;
  try {
    answer = execFileSync('python3', ['-c', PYTHON_COMMENTS], {
      cwd: root,
      input: JSON.stringify(paths),
      encoding: 'utf8',
      maxBuffer: 1 << 26,
    });
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') throw new CannotRun('python3 is not on PATH, so no Python file was read');
    throw error;
  }
  const rows = JSON.parse(answer) as Record<string, number[]>;
  return new Map(Object.entries(rows).map(([path, lines]) => [path, lines.map((line) => ({ line, lines: 1 }))]));
}

type Typescript = typeof import('typescript');

function typescript(): Typescript {
  try {
    return createRequire(import.meta.url)('typescript') as Typescript;
  } catch {
    throw new CannotRun('typescript is not installed; run npm install at the root');
  }
}

export function scriptComments(text: string, path: string): Comment[] {
  const ts = typescript();
  const kind = path.endsWith('.tsx') ? ts.ScriptKind.TSX : path.endsWith('.ts') ? ts.ScriptKind.TS : ts.ScriptKind.JS;
  const file = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true, kind);
  const starts = new Map<number, number>();
  const visit = (node: import('typescript').Node) => {
    for (const range of [
      ...(ts.getLeadingCommentRanges(text, node.getFullStart()) ?? []),
      ...(ts.getTrailingCommentRanges(text, node.getEnd()) ?? []),
    ]) {
      starts.set(range.pos, range.end);
    }
    node.forEachChild(visit);
  };
  visit(file);
  for (const range of ts.getLeadingCommentRanges(text, file.endOfFileToken.getFullStart()) ?? []) starts.set(range.pos, range.end);
  return [...starts.entries()]
    .filter(([pos]) => !(pos === 0 && text.startsWith('#!')))
    .map(([pos, end]) => {
      const first = file.getLineAndCharacterOfPosition(pos).line + 1;
      const last = file.getLineAndCharacterOfPosition(end).line + 1;
      return { line: first, lines: last - first + 1 };
    })
    .sort((a, b) => a.line - b.line);
}

export function sqlComments(text: string): Comment[] {
  const found: Comment[] = [];
  let quoted = false;
  text.split('\n').forEach((line, index) => {
    for (let i = 0; i < line.length; i += 1) {
      if (line[i] === "'") quoted = !quoted;
      if (!quoted && line[i] === '-' && line[i + 1] === '-') {
        found.push({ line: index + 1, lines: 1 });
        break;
      }
    }
  });
  return found;
}

export function commentProblems(path: string, text: string, comments: Comment[]): string[] {
  if (comments.length === 0) return [];
  const firstCode = text.startsWith('#!') ? 2 : 1;
  let header = 0;
  let next = firstCode;
  const rest: Comment[] = [];
  const lines = text.split('\n');
  const wholeLine = (line: number) => /^\s*(#|--|\/\/|\/\*|\*)/.test(lines[line - 1] ?? '');
  for (const comment of comments) {
    if (rest.length === 0 && comment.line === next && wholeLine(comment.line)) {
      header += comment.lines;
      next = comment.line + comment.lines;
    } else {
      rest.push(comment);
    }
  }
  const found: string[] = [];
  if (!isScript(path, text) && header > 0) {
    found.push(`${path}: a comment on line ${firstCode}; hand-written source carries none, and only a script or a test has a header`);
  } else if (header > HEADER_CAP) {
    found.push(`${path}: a header of ${header} lines; a script or a test has one of at most ${HEADER_CAP}`);
  }
  for (const comment of rest) {
    found.push(`${path}: a comment on line ${comment.line}; hand-written source carries none`);
  }
  return found;
}

export function cellProblems(path: string, text: string): string[] {
  return proseLines(text).flatMap((line, index) =>
    line.trim().startsWith('|')
      ? line
          .split(/(?<!\\)\|/)
          .filter((cell) => [...cell].length > CELL_CAP)
          .map(() => `${path}: a table cell on line ${index + 1} passes ${CELL_CAP} characters; a cell that needs a paragraph is a level never written`)
      : [],
  );
}

export function sizeProblems(path: string, text: string, allowances = ALLOWANCES): string[] {
  const size = [...text].length;
  const allowance = allowances.get(path);
  const cap = allowance ? allowance[0] : DOCUMENT_CAP;
  if (size > cap) return [`${path}: ${size} characters, over its cap of ${cap}`];
  if (allowance && size <= DOCUMENT_CAP) return [`ALLOWANCES raises ${path}, which fits the shared cap of ${DOCUMENT_CAP} again`];
  return [];
}

export function problems(root = ROOT, allowances = ALLOWANCES, vendored = VENDORED): string[] {
  const files = walk(root);
  const pages = documents(files).filter((page) => !isDatedProcessDocument(page) && !isSymlink(root, page));
  const code = sources(files, vendored);
  const python = pythonComments(
    root,
    code.filter((path) => path.endsWith('.py')).map((path) => join(root, path)),
  );
  const commentsOf = (path: string, text: string): Comment[] => {
    if (path.endsWith('.py')) return python.get(join(root, path)) ?? [];
    if (path.endsWith('.sql')) return sqlComments(text);
    return scriptComments(text, path);
  };
  return [
    ...zeroScanProblems('documents', pages.length),
    ...zeroScanProblems('source files', code.length),
    ...staleProblems('ALLOWANCES', allowances, (key) => files.includes(key)),
    ...staleProblems('VENDORED', vendored, (key) => files.includes(key)),
    ...pages.flatMap((page) => {
      const text = read(root, page);
      return [...sizeProblems(page, text, allowances), ...cellProblems(page, text)];
    }),
    ...code.flatMap((path) => {
      const text = read(root, path);
      return commentProblems(path, text, commentsOf(path, text));
    }),
  ];
}

if (import.meta.main) runGate(() => problems());
