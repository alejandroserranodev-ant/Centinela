import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { inactiveLine } from './expansion.ts';

test('tells a move the changed rules dropped from one whose parent was retired', () => {
  assert.notEqual(inactiveLine('dropped_by_base'), inactiveLine('parent_retired'));
  assert.match(inactiveLine('dropped_by_base'), /reglas/);
  assert.match(inactiveLine('parent_retired'), /retiró/);
});

test('still says something when the reason is missing', () => {
  assert.equal(inactiveLine(null), 'Ya no se aplica.');
});
