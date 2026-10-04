import { posix } from 'node:path';
import { runGate, staleProblems, zeroScanProblems } from './gate.ts';
import {
  ROOT,
  anchors,
  codeSpans,
  directories,
  documents,
  ignored,
  isDatedProcessDocument,
  isExternal,
  isSymlink,
  links,
  nearestManifestDirectory,
  proseLines,
  read,
  resolveFrom,
  walk,
} from './tree.ts';

export const EXEMPT_DOCUMENTS = new Map<string, string>([
  ['docs_guide.md', 'it describes Arena, another tree, and its own last section says no citation gate applies to it'],
]);

export const EXEMPT = new Map<string, string>([
  ['AGENTS.md → path/to/file.py:member(parameters)', 'the citation rule shows the form it asks for with a path that names no file'],
]);

const EXTENSIONS = 'md|py|ts|tsx|js|mjs|cjs|json|yaml|yml|sql|csv|toml|html|css|pdf|xlsx|lock|txt|sh|cfg|ini';
const BARE_FILE = new RegExp(`^[\\w.@-]+\\.(?:${EXTENSIONS})$`);
const DOTFILE = /^\.[\w-]+(?:\.[\w-]+)*$/;
const PATH = /^\.{0,2}\/?[\w.@-]+(?:\/[\w.@-]+)+\/?$/;
const LINE_CITATION = /^([\w./@-]+\.[A-Za-z]+):(\d+)/;
const MEMBER_CITATION = /^([\w./@-]+\.(py|ts|tsx|js|mjs)):([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)?)(\(.*\))?$/;
const FILE_CITATION = new RegExp(`^([\\w./@-]+\\.(?:${EXTENSIONS})):[A-Za-z_\\w.$/-]+(\\(.*\\))?$`);

export function pathLike(span: string): boolean {
  if (/\s/.test(span) || /[*<>{}$|"'(),=:]/.test(span)) return false;
  if (span.startsWith('@') || span.startsWith('-') || span.startsWith('/')) return false;
  if (new RegExp(`^\\.(?:${EXTENSIONS})$`).test(span)) return false;
  return PATH.test(span) || /^[\w.@-]+\/$/.test(span) || BARE_FILE.test(span) || DOTFILE.test(span);
}

export function candidates(files: string[], page: string, path: string): string[] {
  const base = posix.dirname(page);
  const pack = nearestManifestDirectory(files, page);
  const from = ['.', base, ...(pack ? [pack] : [])];
  return [...new Set(from.map((dir) => resolveFrom(dir, path)))];
}

function escape(name: string): string {
  return name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function declares(text: string, member: string, language: string): boolean {
  const [owner, inner] = member.includes('.') ? member.split('.') : [undefined, member];
  const name = escape(inner);
  if (language === 'py') {
    const ownerFound = owner === undefined || new RegExp(`^\\s*class\\s+${escape(owner)}\\b`, 'm').test(text);
    const forms = [
      new RegExp(`^\\s*(?:async\\s+)?(?:def|class)\\s+${name}\\b`, 'm'),
      new RegExp(`^${name}\\s*(?::[^=\\n]*)?=`, 'm'),
      ...(owner === undefined ? [] : [new RegExp(`^\\s+${name}\\s*(?::|=)`, 'm')]),
    ];
    return ownerFound && forms.some((form) => form.test(text));
  }
  const ownerFound =
    owner === undefined || new RegExp(`(?:class|interface|type|const|function)\\s+${escape(owner)}\\b`).test(text);
  const forms = [
    new RegExp(`(?:function\\*?|const|let|var|class|type|interface|enum)\\s+${name}\\b`),
    new RegExp(`export\\s*\\{[^}]*\\b${name}\\b`),
    ...(owner === undefined ? [] : [new RegExp(`\\b${name}\\s*[(:=?]`)]),
  ];
  return ownerFound && forms.some((form) => form.test(text));
}

type Unresolved = { key: string; problem: string };

export function pageProblems(root: string, files: string[], page: string): Unresolved[] {
  const known = new Set(files);
  const dirs = directories(files);
  const exists = (path: string) => known.has(path) || dirs.has(path) || path === '.';
  const found: Unresolved[] = [];
  const unresolved = (subject: string, problem: string) =>
    found.push({ key: `${page} → ${subject}`, problem: `${page}: ${problem}` });
  const locate = (path: string) => candidates(files, page, path.replace(/\/$/, '')).find(exists);
  const text = read(root, page);
  for (const line of proseLines(text)) {
    for (const target of links(line)) {
      if (isExternal(target)) continue;
      const [path, anchor] = target.split('#');
      const resolved = path === '' ? page : resolveFrom(posix.dirname(page), decodeURI(path));
      if (!exists(resolved) && !ignored(root, resolved)) {
        unresolved(target, `the link ${target} resolves to nothing`);
        continue;
      }
      if (anchor && resolved.endsWith('.md') && known.has(resolved) && !anchors(read(root, resolved)).has(anchor)) {
        unresolved(target, `the link ${target} names an anchor ${resolved} has no heading for`);
      }
    }
    for (const span of codeSpans(line)) {
      if (LINE_CITATION.test(span)) {
        unresolved(span, `\`${span}\` cites code by line number; cite path:member(parameters)`);
        continue;
      }
      const member = MEMBER_CITATION.exec(span);
      const cited = member ? member[1] : FILE_CITATION.exec(span)?.[1];
      if (cited !== undefined) {
        const file = locate(cited);
        if (file === undefined) {
          unresolved(span, `\`${span}\` names ${cited}, which resolves from neither the root, beside the page nor its package`);
        } else if (member && !declares(read(root, file), member[3], member[2] === 'py' ? 'py' : 'ts')) {
          unresolved(span, `\`${span}\` names ${member[3]}, which ${file} does not declare`);
        }
        continue;
      }
      if (!pathLike(span)) continue;
      const suffix = span.endsWith('/') ? '/' : '';
      if (locate(span) === undefined && !candidates(files, page, span).some((path) => ignored(root, path + suffix))) {
        unresolved(span, `\`${span}\` resolves from neither the root, beside the page nor its package`);
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
