import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { canConfigure, roleLabel, roleName } from './roles.ts';

test('names each role in Spanish and a process leader with its area', () => {
  assert.equal(roleLabel({ role: 'gerente', area: null }), 'Gerente');
  assert.equal(roleLabel({ role: 'lider_proceso', area: 'Compras' }), 'Líder de proceso · Compras');
  assert.equal(roleLabel({ role: 'analista', area: null }), 'Analista');
  assert.equal(roleLabel({ role: 'auditor', area: null }), 'Auditoría');
});

test('names a role a log row carries, and keeps one it does not know', () => {
  assert.equal(roleName('lider_proceso'), 'Líder de proceso');
  assert.equal(roleName('auditor'), 'Auditoría');
  assert.equal(roleName('otro'), 'otro');
});

test('only the analyst and the manager change the settings', () => {
  assert.equal(canConfigure({ role: 'analista' }), true);
  assert.equal(canConfigure({ role: 'gerente' }), true);
  assert.equal(canConfigure({ role: 'lider_proceso' }), false);
  assert.equal(canConfigure({ role: 'auditor' }), false);
});
