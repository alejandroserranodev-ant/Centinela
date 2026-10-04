import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { explainedByRemaining } from './alert.ts';

test('a merged alert with no cause of its own is explained by the alert that remains', () => {
  assert.equal(explainedByRemaining({ kind: 'no_evidence' }, true), true);
  assert.equal(explainedByRemaining({ kind: 'identified' }, true), false);
  assert.equal(explainedByRemaining({ kind: 'no_evidence' }, false), false);
});
