import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { bearer, getToken, notifyUnauthorized, onUnauthorized, setToken } from './session.ts';

test('holds the token without a sessionStorage and sends it as a bearer header', () => {
  setToken(null);
  assert.equal(getToken(), null);
  assert.deepEqual(bearer(), {});
  setToken('abc.def');
  assert.equal(getToken(), 'abc.def');
  assert.deepEqual(bearer(), { Authorization: 'Bearer abc.def' });
});

test('a 401 clears the token and calls the registered callback once', () => {
  setToken('abc.def');
  let calls = 0;
  onUnauthorized(() => {
    calls += 1;
  });
  notifyUnauthorized('abc.def');
  assert.equal(getToken(), null);
  assert.equal(calls, 1);
  onUnauthorized(null);
  notifyUnauthorized(null);
  assert.equal(calls, 1);
});

test('a late 401 for an older token leaves the newer one in place', () => {
  setToken('new.token');
  let calls = 0;
  onUnauthorized(() => {
    calls += 1;
  });
  notifyUnauthorized('old.token');
  assert.equal(getToken(), 'new.token');
  assert.equal(calls, 0);
  onUnauthorized(null);
});
