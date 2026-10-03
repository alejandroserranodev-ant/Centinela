import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ALLOWANCES, CELL_CAP, DOCUMENT_CAP, VENDORED, problems } from './check-docs.ts';
import { plant } from './support.ts';

const sound = {
  'AGENTS.md': '# Root\n\n| a | b |\n|---|---|\n| short | cell |\n',
  'pkg/mod.py': 'def run():\n    return "# not a comment"\n',
  'pkg/tests/test_mod.py': '# One header line.\n# A second one.\n\ndef test_run():\n    pass\n',
  'web/app.tsx': 'export const url = "http://x//y";\nexport const node = <a href="//x">a // b</a>;\n',
  'web/run.test.ts': '// The header of a test.\nexport const ok = 1;\n',
  'sql/views.sql': "select '--' as dash;\n",
};

test('a sound tree passes', () => {
  assert.deepEqual(problems(plant(sound), new Map(), new Map()), []);
});

test('the maps hold what they say', () => {
  assert.deepEqual([...ALLOWANCES.keys()], []);
  assert.deepEqual([...VENDORED.keys()], [
    'data/sql/01_esquema.sql',
    'data/sql/02_carga.sql',
    'data/sql/03_capa_semantica.sql',
    'data/generator/generar_dataset.py',
  ]);
  for (const reason of VENDORED.values()) assert.match(reason, /kit/);
});

test('a comment in hand-written Python fails', () => {
  const found = problems(plant({ ...sound, 'pkg/mod.py': 'def run():\n    return 1  # why\n' }), new Map(), new Map());
  assert.deepEqual(found, ['pkg/mod.py: a comment on line 2; hand-written source carries none']);
});

test('a header on a module that is not a script fails', () => {
  const found = problems(plant({ ...sound, 'pkg/mod.py': '# A header.\ndef run():\n    pass\n' }), new Map(), new Map());
  assert.deepEqual(found, ['pkg/mod.py: a comment on line 1; hand-written source carries none, and only a script or a test has a header']);
});

test('a test header over ten lines fails', () => {
  const header = Array.from({ length: 11 }, (_, i) => `# line ${i}`).join('\n');
  const found = problems(plant({ ...sound, 'pkg/tests/test_mod.py': `${header}\ndef test_run():\n    pass\n` }), new Map(), new Map());
  assert.deepEqual(found, ['pkg/tests/test_mod.py: a header of 11 lines; a script or a test has one of at most 10']);
});

test('a comment in TypeScript fails, and a block comment counts as one', () => {
  const found = problems(
    plant({ ...sound, 'web/app.tsx': 'export const a = 1;\n/* two\n lines */\nexport const b = 2; // why\n' }),
    new Map(),
    new Map(),
  );
  assert.deepEqual(found, [
    'web/app.tsx: a comment on line 2; hand-written source carries none',
    'web/app.tsx: a comment on line 4; hand-written source carries none',
  ]);
});

test('a SQL script keeps its header, and a comment below it fails', () => {
  const found = problems(plant({ ...sound, 'sql/views.sql': '-- The header.\nselect 1; -- why\n' }), new Map(), new Map());
  assert.deepEqual(found, ['sql/views.sql: a comment on line 2; hand-written source carries none']);
});

test('a vendored file is not read', () => {
  const tree = plant({ ...sound, 'kit/load.sql': '-- as delivered\n' });
  assert.deepEqual(problems(tree, new Map(), new Map([['kit/load.sql', 'kit']])), []);
});

test('a document over the cap fails, and an allowance raises it', () => {
  const big = '# Big\n\n' + 'word '.repeat(DOCUMENT_CAP / 5 + 10);
  const tree = plant({ ...sound, 'big.md': big });
  assert.match(problems(tree, new Map(), new Map())[0], /^big\.md: \d+ characters, over its cap of 60000$/);
  assert.deepEqual(problems(tree, new Map([['big.md', [70000, 'reason']]]), new Map()), []);
});

test('an allowance on a document back under the shared cap is stale', () => {
  const found = problems(plant(sound), new Map([['AGENTS.md', [70000, 'reason']]]), new Map());
  assert.deepEqual(found, ['ALLOWANCES raises AGENTS.md, which fits the shared cap of 60000 again']);
});

test('a table cell over its cap fails', () => {
  const found = problems(plant({ ...sound, 'AGENTS.md': `| a |\n|---|\n| ${'x'.repeat(CELL_CAP + 1)} |\n` }), new Map(), new Map());
  assert.deepEqual(found, ['AGENTS.md: a table cell on line 3 passes 2000 characters; a cell that needs a paragraph is a level never written']);
});

test('a stale vendored entry fails', () => {
  const found = problems(plant(sound), new Map(), new Map([['kit/gone.sql', 'kit']]));
  assert.deepEqual(found, ['VENDORED names kit/gone.sql, which the tree no longer holds']);
});

test('a tree with no source fails as a zero scan', () => {
  const found = problems(plant({ 'AGENTS.md': '# Root\n' }), new Map(), new Map());
  assert.deepEqual(found, ['walked 0 source files, so every rule below passes over a tree it never opened']);
});
