import { strict as assert } from 'node:assert';
import { test } from 'node:test';

import { readSse } from './sse.ts';

function streamOf(...pieces: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const piece of pieces) controller.enqueue(encoder.encode(piece));
      controller.close();
    },
  });
}

async function collect(body: ReadableStream<Uint8Array>) {
  const events = [];
  for await (const event of readSse(body)) events.push(event);
  return events;
}

test('takes the event name from the event line and the payload from the data line', async () => {
  const events = await collect(
    streamOf(
      'event: step\ndata: {"agent":"vigia","status":"running"}\n\n',
      'event: end\ndata: {"simulatedDay":"2026-10-04","newAlerts":["a1"]}\n\n',
    ),
  );
  assert.deepEqual(events, [
    { event: 'step', data: { agent: 'vigia', status: 'running' } },
    { event: 'end', data: { simulatedDay: '2026-10-04', newAlerts: ['a1'] } },
  ]);
});

test('joins an event split across pieces', async () => {
  const events = await collect(streamOf('event: en', 'd\ndata: {"newAl', 'erts":[]}\n', '\n'));
  assert.deepEqual(events, [{ event: 'end', data: { newAlerts: [] } }]);
});

test('reads a last event the stream closes without a blank line', async () => {
  const events = await collect(streamOf('event: end\ndata: {"x":1}\n'));
  assert.deepEqual(events, [{ event: 'end', data: { x: 1 } }]);
});
