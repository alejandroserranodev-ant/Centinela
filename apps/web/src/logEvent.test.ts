import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import type { LogEvent } from './api/types';
import { latestResult, withoutAlert } from './logEvent.ts';

test('names what a row with no alert belongs to by its type', () => {
  assert.equal(withoutAlert('configuracion'), 'Configuración');
  assert.equal(withoutAlert('question'), 'Chat, sin alerta');
  assert.equal(withoutAlert('refusal'), 'Chat, sin alerta');
  assert.equal(withoutAlert('result'), 'Sin alerta');
});

test('reads the newest result of an alert, which the log lists first', () => {
  const row = (id: string, type: LogEvent['type'], detail: string): LogEvent => ({
    id,
    date: '2026-10-04T00:00:00Z',
    simulatedDay: '2026-09-01',
    alertId: 'a1',
    type,
    actor: { kind: 'agent', agent: 'ejecutor' },
    detail,
    queryId: null,
    figures: [],
  });
  const events = [row('3', 'decision', 'Aprobada'), row('2', 'result', 'La acción aprobada no se ejecutó: x'), row('1', 'result', 'antes')];
  assert.equal(latestResult(events)?.detail, 'La acción aprobada no se ejecutó: x');
  assert.equal(latestResult([row('3', 'decision', 'Aprobada')]), null);
});
