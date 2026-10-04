import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { test } from 'node:test';
import { OPENAPI, SCHEMA, problems } from './check-contract.ts';
import { plant } from './support.ts';

const sound = {
  [OPENAPI]: '{}\n',
  [SCHEMA]: 'export interface paths {}\n',
  'apps/web/package.json': '{}',
};

const writes = (text: string) => (_root: string, output: string) => {
  writeFileSync(output, text);
  return output;
};

test('a schema equal to what the generator writes passes', () => {
  assert.deepEqual(problems(plant(sound), writes('export interface paths {}\n')), []);
});

test('a schema that differs from what the generator writes fails', () => {
  const found = problems(plant(sound), writes('export interface paths { a: 1 }\n'));
  assert.deepEqual(found, [`${SCHEMA} differs from what the generator writes from ${OPENAPI}; run npm run contract in apps/web`]);
});

test('a missing exported document fails before the generator runs', () => {
  const { [OPENAPI]: _, ...rest } = sound;
  const found = problems(plant(rest), () => {
    throw new Error('the generator must not run');
  });
  assert.deepEqual(found, [`${OPENAPI} is missing; run python -m centinela_api.contrato, then npm run contract in apps/web`]);
});
