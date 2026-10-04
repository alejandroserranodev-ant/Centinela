import assert from 'node:assert/strict';
import { test } from 'node:test';
import { EXEMPT, EXEMPT_DOCUMENTS, problems } from './check-vocabulary.ts';
import { plant } from './support.ts';

const sound = {
  'AGENTS.md': '# Root\n\nRun `npm run check` here, and `npm install` in `web`.\n\n```bash\ncd py && uv run pytest\n```\n',
  'docs_guide.md': '`bun run check:everything`\n',
  'package.json': '{"scripts":{"check":"x"}}',
  'web/AGENTS.md': '# Web\n\n`npm run dev` and `npm test`.\n',
  'web/package.json': '{"scripts":{"dev":"vite","test":"x"}}',
  'py/AGENTS.md': '# Py\n\n`uv run python -m pkg.generate`, `uv run pytest tests/test_a.py` and `uv run python tools/run.py`.\n',
  'py/pyproject.toml': '[dependency-groups]\ndev = ["pytest>=8"]\n',
  'py/pkg/__init__.py': '',
  'py/pkg/generate.py': '',
  'py/tools/run.py': '',
  'py/tests/test_a.py': '',
};

test('a sound tree passes', () => {
  assert.deepEqual(problems(plant(sound)), []);
});

test('the maps hold what they say', () => {
  assert.deepEqual([...EXEMPT_DOCUMENTS.keys()], ['docs_guide.md']);
  assert.match(EXEMPT_DOCUMENTS.get('docs_guide.md') as string, /Bun/);
  assert.deepEqual([...EXEMPT.keys()], []);
});

test('an npm script the nearest manifest lacks fails', () => {
  const found = problems(plant({ ...sound, 'web/AGENTS.md': '`npm run build`\n' }));
  assert.deepEqual(found, ['web/AGENTS.md: `npm run build` runs npm script build, and web/package.json declares no npm script build']);
});

test('a module the package lacks fails', () => {
  const found = problems(plant({ ...sound, 'py/AGENTS.md': '`uv run python -m pkg.gone`\n' }));
  assert.deepEqual(found, ['py/AGENTS.md: `uv run python -m pkg.gone` runs module pkg.gone, and py/pyproject.toml declares no module pkg.gone']);
});

test('a tool no dependency group holds fails', () => {
  const found = problems(plant({ ...sound, 'py/AGENTS.md': '`uv run ruff check`\n' }));
  assert.deepEqual(found, ['py/AGENTS.md: `uv run ruff check` runs tool ruff, and py/pyproject.toml declares no tool ruff']);
});

test('a test file that is gone fails', () => {
  const found = problems(plant({ ...sound, 'py/AGENTS.md': '`uv run pytest tests/test_gone.py`\n' }));
  assert.deepEqual(found, ['py/AGENTS.md: `uv run pytest tests/test_gone.py` runs tool pytest with tests/test_gone.py, and py/pyproject.toml declares no tool pytest with tests/test_gone.py']);
});

test('a script path that is gone fails', () => {
  const found = problems(plant({ ...sound, 'py/AGENTS.md': '`uv run python tools/gone.py`\n' }));
  assert.deepEqual(found, ['py/AGENTS.md: `uv run python tools/gone.py` runs script tools/gone.py, and py/pyproject.toml declares no script tools/gone.py']);
});

test('a command in a fence is checked against the directory it changes into', () => {
  const found = problems(plant({ ...sound, 'AGENTS.md': '# Root\n\n```bash\ncd web && npm run lint\n```\n' }));
  assert.deepEqual(found, ['AGENTS.md: `cd web && npm run lint` runs npm script lint, and web/package.json declares no npm script lint']);
});

test('a python script that is gone fails', () => {
  const found = problems(plant({ ...sound, 'py/AGENTS.md': '`python3 gone.py`\n' }));
  assert.deepEqual(found, ['py/AGENTS.md: `python3 gone.py` runs script gone.py, and neither py nor . holds it']);
});

test('a uv command no pyproject governs fails', () => {
  const found = problems(plant({ ...sound, 'AGENTS.md': '# Root\n\n`uv run pytest`\n' }));
  assert.deepEqual(found, ['AGENTS.md: `uv run pytest` runs tool pytest, and no pyproject.toml governs the page']);
});

test('a stale exemption fails', () => {
  const found = problems(plant(sound), new Map([['AGENTS.md → npm run gone', 'x']]));
  assert.deepEqual(found, ['EXEMPT names AGENTS.md → npm run gone, which the tree no longer holds']);
});

test('a tree with no documents fails as a zero scan', () => {
  assert.match(problems(plant({ 'docs_guide.md': 'x\n' }))[0], /^walked 0 documents/);
});
