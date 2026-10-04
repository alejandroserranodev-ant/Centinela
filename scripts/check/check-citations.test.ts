import assert from 'node:assert/strict';
import { test } from 'node:test';
import { EXEMPT, EXEMPT_DOCUMENTS, problems as gate } from './check-citations.ts';
import { plant } from './support.ts';

const problems = (root: string, exempt = new Map<string, string>()) => gate(root, exempt);

const sound = {
  'AGENTS.md': '# Root\n\nSee [`pkg/AGENTS.md`](./pkg/AGENTS.md#the-rules) and `pkg/src/mod.py:run(day)`.\n',
  'docs_guide.md': 'Cites `arena/nowhere.ts:gone()`.\n',
  'pkg/AGENTS.md': '# Pkg\n\n## The rules\n\nThe code is `src/mod.py:Thing.go`, `src/app.ts:render(props)` and `src/`.\n',
  'pkg/pyproject.toml': '[project]\nname = "pkg"\n',
  'pkg/src/mod.py': 'class Thing:\n    def go(self):\n        pass\n\n\ndef run(day):\n    pass\n',
  'pkg/src/app.ts': 'export function render(props: unknown) {}\n',
};

test('a sound tree passes', () => {
  assert.deepEqual(problems(plant(sound)), []);
});

test('the maps hold what they say', () => {
  assert.deepEqual([...EXEMPT_DOCUMENTS.keys()], ['docs_guide.md']);
  assert.match(EXEMPT_DOCUMENTS.get('docs_guide.md') as string, /another tree/);
  assert.deepEqual([...EXEMPT.keys()], ['AGENTS.md → path/to/file.py:member(parameters)']);
  assert.match(EXEMPT.get('AGENTS.md → path/to/file.py:member(parameters)') as string, /form/);
});

test('a broken link fails', () => {
  const found = problems(plant({ ...sound, 'AGENTS.md': '[x](./gone.md)\n' }));
  assert.deepEqual(found, ['AGENTS.md: the link ./gone.md resolves to nothing']);
});

test('a missing anchor fails', () => {
  const found = problems(plant({ ...sound, 'AGENTS.md': '[x](./pkg/AGENTS.md#nowhere)\n' }));
  assert.deepEqual(found, ['AGENTS.md: the link ./pkg/AGENTS.md#nowhere names an anchor pkg/AGENTS.md has no heading for']);
});

test('a path that resolves nowhere fails', () => {
  const found = problems(plant({ ...sound, 'pkg/AGENTS.md': '# Pkg\n\n## The rules\n\n`src/gone.py`\n' }));
  assert.deepEqual(found, ['pkg/AGENTS.md: `src/gone.py` resolves from neither the root, beside the page nor its package']);
});

test('a bare sibling filename from another level fails', () => {
  const found = problems(plant({ ...sound, 'AGENTS.md': '# Root\n\n[p](./pkg/AGENTS.md) `mod.py`\n' }));
  assert.deepEqual(found, ['AGENTS.md: `mod.py` resolves from neither the root, beside the page nor its package']);
});

test('a member the file does not declare fails, in Python and TypeScript', () => {
  const found = problems(
    plant({ ...sound, 'pkg/AGENTS.md': '# Pkg\n\n## The rules\n\n`src/mod.py:walk(day)` `src/app.ts:paint()` `src/mod.py:Thing.stop`\n' }),
  );
  assert.deepEqual(found, [
    'pkg/AGENTS.md: `src/mod.py:walk(day)` names walk, which pkg/src/mod.py does not declare',
    'pkg/AGENTS.md: `src/app.ts:paint()` names paint, which pkg/src/app.ts does not declare',
    'pkg/AGENTS.md: `src/mod.py:Thing.stop` names Thing.stop, which pkg/src/mod.py does not declare',
  ]);
});

test('a generator function is a member a TypeScript file declares', () => {
  const found = problems(
    plant({
      ...sound,
      'pkg/AGENTS.md': '# Pkg\n\n## The rules\n\n`src/stream.ts:advance(days)`\n',
      'pkg/src/stream.ts': 'export async function* advance(days: number) {}\n',
    }),
  );
  assert.deepEqual(found, []);
});

test('a citation by line number fails', () => {
  const found = problems(plant({ ...sound, 'pkg/AGENTS.md': '# Pkg\n\n## The rules\n\n`src/mod.py:12`\n' }));
  assert.deepEqual(found, ['pkg/AGENTS.md: `src/mod.py:12` cites code by line number; cite path:member(parameters)']);
});

test('a fenced block is not checked', () => {
  assert.deepEqual(problems(plant({ ...sound, 'AGENTS.md': '```\n`gone/file.py` [x](./gone.md)\n```\n' })), []);
});

test('an exemption that no longer excuses anything is stale', () => {
  const exempt = new Map([['AGENTS.md → gone/file.py', 'decided, not built']]);
  const found = problems(plant(sound), exempt);
  assert.deepEqual(found, ['EXEMPT names AGENTS.md → gone/file.py, which the tree no longer holds']);
});

test('an exemption excuses its own path', () => {
  const exempt = new Map([['AGENTS.md → gone/file.py', 'decided, not built']]);
  assert.deepEqual(problems(plant({ ...sound, 'AGENTS.md': '`gone/file.py`\n' }), exempt), []);
});

test('a stale exempt document fails', () => {
  const { 'docs_guide.md': _, ...rest } = sound;
  assert.deepEqual(problems(plant(rest)), ['EXEMPT_DOCUMENTS names docs_guide.md, which the tree no longer holds']);
});

test('a tree with no documents fails as a zero scan', () => {
  const found = problems(plant({ 'docs_guide.md': 'x\n' }));
  assert.match(found[0], /^walked 0 documents/);
});
