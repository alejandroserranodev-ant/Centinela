export interface RawSseEvent {
  event: string;
  data: unknown;
}

function parseBlock(block: string): RawSseEvent | null {
  let event = 'message';
  const data: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      data.push(line.slice(5).replace(/^ /, ''));
    }
  }
  if (data.length === 0) {
    return null;
  }
  return { event, data: JSON.parse(data.join('\n')) };
}

export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<RawSseEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n?/g, '\n');
      const blocks = buffer.split('\n\n');
      buffer = done ? '' : (blocks.pop() ?? '');
      for (const block of blocks) {
        const parsed = parseBlock(block);
        if (parsed) {
          yield parsed;
        }
      }
      if (done) {
        break;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
