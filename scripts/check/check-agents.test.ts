import assert from 'node:assert/strict';
import { test } from 'node:test';
import { SURVIVORS, problems } from './check-agents.ts';
import { ROUTER, plant } from './support.ts';

const sound = {
  'AGENTS.md': ROUTER,
  'CLAUDE.md': { symlink: 'AGENTS.md' },
  'README.md': 'See [AGENTS.md](./AGENTS.md).\n',
  'a/AGENTS.md': '# a\n',
};

test('a sound tree passes', () => {
  assert.deepEqual(problems(plant(sound)), []);
});

test('SURVIVORS keeps the root README, with its reason', () => {
  assert.deepEqual([...SURVIVORS.keys()], ['README.md']);
  assert.match(SURVIVORS.get('README.md') as string, /router/);
});

test('a level no link reaches fails', () => {
  const found = problems(plant({ ...sound, 'b/AGENTS.md': '# b\n' }));
  assert.deepEqual(found, ['b/AGENTS.md is a level no chain of links from AGENTS.md reaches']);
});

test('a link inside a fence reaches nothing', () => {
  const found = problems(plant({ ...sound, 'AGENTS.md': ROUTER + '\n```\n[b](./b/AGENTS.md)\n```\n', 'b/AGENTS.md': '# b\n' }));
  assert.equal(found.length, 1);
});

test('a second README fails', () => {
  const found = problems(plant({ ...sound, 'a/README.md': 'x\n' }));
  assert.deepEqual(found, ['a/README.md is a README outside SURVIVORS; README.md at the root is the only one']);
});

test('a CLAUDE.md that is a file fails', () => {
  const found = problems(plant({ ...sound, 'CLAUDE.md': ROUTER }));
  assert.deepEqual(found, ['CLAUDE.md is not a symlink to AGENTS.md']);
});

test('a manifest with no page beside it fails', () => {
  const found = problems(plant({ ...sound, 'c/package.json': '{}' }));
  assert.deepEqual(found, ['c holds a manifest and no AGENTS.md beside it to name its commands']);
});

test('a stale survivor fails', () => {
  const { 'README.md': _, ...rest } = sound;
  const found = problems(plant(rest));
  assert.deepEqual(found, ['SURVIVORS names README.md, which the tree no longer holds']);
});

test('a tree with no AGENTS.md fails as a zero scan', () => {
  const found = problems(plant({ 'README.md': 'x\n', 'CLAUDE.md': { symlink: 'AGENTS.md' } }));
  assert.match(found[0], /^walked 0 AGENTS.md pages/);
});
