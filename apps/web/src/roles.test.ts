import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { roleLabel } from './roles.ts';

test('names each role in Spanish and a process leader with its area', () => {
  assert.equal(roleLabel({ role: 'gerente', area: null }), 'Gerente');
  assert.equal(roleLabel({ role: 'lider_proceso', area: 'Compras' }), 'Líder de proceso · Compras');
  assert.equal(roleLabel({ role: 'analista', area: null }), 'Analista');
  assert.equal(roleLabel({ role: 'auditor', area: null }), 'Auditoría');
});
