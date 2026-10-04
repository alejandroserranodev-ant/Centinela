import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { messageOfError, OFFLINE, reach } from './error-message.ts';

test('reads a string detail as the message', () => {
  assert.equal(messageOfError('{"detail":"Ya hay un día en curso"}', 'Conflict'), 'Ya hay un día en curso');
});

test('reads the first msg of a validation detail list', () => {
  const body = JSON.stringify({ detail: [{ msg: 'String should have at most 500 characters' }, { msg: 'otro' }] });
  assert.equal(messageOfError(body, 'Unprocessable Entity'), 'String should have at most 500 characters');
});

test('falls back to the text of a body that is not JSON, then to the status text', () => {
  assert.equal(messageOfError('Bad gateway', 'Bad Gateway'), 'Bad gateway');
  assert.equal(messageOfError('', 'Bad Gateway'), 'Bad Gateway');
});

test('falls back to the body when the JSON carries no usable detail', () => {
  assert.equal(messageOfError('{"x":1}', 'Teapot'), '{"x":1}');
});

test('turns a request that never reaches the API into the Spanish offline message', async () => {
  await assert.rejects(
    reach(() => Promise.reject(new TypeError('Failed to fetch')), (message) => new Error(message)),
    { message: OFFLINE },
  );
});

test('lets an aborted request stay an abort', async () => {
  await assert.rejects(
    reach(() => Promise.reject(new DOMException('aborted', 'AbortError')), (message) => new Error(message)),
    { name: 'AbortError' },
  );
});
