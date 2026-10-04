import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { fillSentence, formatFigureInText } from './format.ts';

test('fills each placeholder with its figure and keeps one that has none', () => {
  const pesos = { value: 1500000, unit: 'COP', queryId: 'q1' } as const;
  const dias = { value: 45, unit: 'days', queryId: 'q2' } as const;
  assert.equal(
    fillSentence('C0416 debe {0} a {1} días y {2}.', [pesos, dias]),
    `C0416 debe ${formatFigureInText(pesos)} a ${formatFigureInText(dias)} días y {2}.`,
  );
});
