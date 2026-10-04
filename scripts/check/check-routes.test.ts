import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ENTRIES, ROUTES, type Budget, problems, rows } from './check-routes.ts';
import { plant } from './support.ts';

const router =
  '# Router\n\n| I am here because | Start at |\n|---|---|\n| a thing | [`a/AGENTS.md`](./a/AGENTS.md), then [`b/AGENTS.md`](./b/AGENTS.md#x) |\n\n**Nothing below the table routes.**\n';

const sound = {
  'AGENTS.md': router,
  'a/AGENTS.md': 'a'.repeat(100),
  'b/AGENTS.md': 'b'.repeat(50),
};

const entries = new Map<string, Budget>([['AGENTS.md', [router.length, 'the router is read whole']]]);
const routes = new Map<string, Budget>([['a thing', [150, 'two stops a reader of a thing pays']]]);

test('a sound tree passes', () => {
  assert.deepEqual(problems(plant(sound), entries, routes), []);
});

test('the router has a budget with its reason', () => {
  assert.deepEqual([...ENTRIES.keys()], ['AGENTS.md']);
  for (const [, [, reason]] of [...ENTRIES, ...ROUTES]) assert.doesNotMatch(reason, /\d|raised|lowered/);
  assert.ok(ROUTES.has('adding a screen'));
});

test('a row reads its stops in order, once each', () => {
  assert.deepEqual(rows(router), [{ question: 'a thing', stops: ['a/AGENTS.md', 'b/AGENTS.md'] }]);
});

test('a route over its budget fails', () => {
  const found = problems(plant({ ...sound, 'b/AGENTS.md': 'b'.repeat(60) }), entries, routes);
  assert.deepEqual(found, ['the route "a thing" costs 160 characters, over its budget of 150']);
});

test('a route far under its budget is stale', () => {
  const found = problems(plant({ ...sound, 'b/AGENTS.md': 'b' }), entries, routes);
  assert.deepEqual(found, ['the route "a thing" costs 101 characters, more than 15% under its budget of 150, which is stale']);
});

test('a row with no budget fails, and a budget with no row is stale', () => {
  const found = problems(plant(sound), entries, new Map<string, Budget>([['gone', [1, 'x']]]));
  assert.deepEqual(found, ['ROUTES names gone, which the tree no longer holds', 'the router row "a thing" has no budget in ROUTES']);
});

test('a reason that names a figure or its history fails', () => {
  const found = problems(plant(sound), entries, new Map<string, Budget>([['a thing', [150, 'raised to 150']]]));
  assert.deepEqual(found, [
    `the route "a thing"'s reason names a figure; a reason says why the budget is right today`,
    `the route "a thing"'s reason tells its history; the commit that moved it carries that`,
  ]);
});

test('the router over its own budget fails', () => {
  const found = problems(plant(sound), new Map<string, Budget>([['AGENTS.md', [10, 'the router']]]), routes);
  assert.deepEqual(found, [`AGENTS.md costs ${router.length} characters, over its budget of 10`]);
});

test('a router with no table fails as a zero scan', () => {
  const found = problems(plant({ 'AGENTS.md': '# Router\n' }), new Map(), new Map());
  assert.deepEqual(found, ['walked 0 router rows, so every rule below passes over a tree it never opened']);
});
