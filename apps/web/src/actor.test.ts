import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { agentName, who } from './actor.ts';

test('names an agent by the stage it works at, never by its own name', () => {
  assert.equal(agentName('estratega'), 'Centinela · propuesta');
  assert.equal(who({ kind: 'agent', agent: 'vigia' }), 'Centinela · detección');
});

test('names a person with the role in Spanish', () => {
  assert.equal(who({ kind: 'person', name: 'Ana', role: 'gerente' } as never), 'Ana (Gerente)');
});
