import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { GATES, scriptOf } from './check-all.ts';
import { ROOT } from './tree.ts';

test('the registry holds every gate, by literal value', () => {
  assert.deepEqual(GATES, [
    'check:agents',
    'check:citations',
    'check:vocabulary',
    'check:docs',
    'check:generated',
    'check:routes',
  ]);
});

test('every check: script of the manifest is in the registry, and the reverse', () => {
  const scripts = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8')).scripts as Record<string, string>;
  const declared = Object.keys(scripts).filter((name) => name.startsWith('check:'));
  assert.deepEqual([...declared].sort(), [...GATES].sort());
  for (const gate of GATES) {
    assert.equal(scripts[gate], `node scripts/check/${gate.replace(':', '-')}.ts`);
    assert.ok(existsSync(scriptOf(gate)), `${gate} has no file`);
  }
});
