import { spawnSync } from 'node:child_process';
import { join } from 'node:path';
import { CANNOT_RUN, PASS } from './gate.ts';
import { ROOT } from './tree.ts';

export const GATES = [
  'check:agents',
  'check:citations',
  'check:vocabulary',
  'check:docs',
  'check:generated',
  'check:routes',
];

export function scriptOf(gate: string): string {
  return join(ROOT, 'scripts/check', `${gate.replace(':', '-')}.ts`);
}

export function sweep(): number {
  const results = GATES.map((gate) => {
    console.log(`── ${gate}`);
    const run = spawnSync(process.execPath, [scriptOf(gate)], { cwd: ROOT, stdio: 'inherit' });
    return { gate, status: run.status ?? 1 };
  });
  const failed = results.filter((one) => one.status !== PASS && one.status !== CANNOT_RUN);
  const skipped = results.filter((one) => one.status === CANNOT_RUN);
  for (const one of results) {
    console.log(`${one.status === PASS ? 'PASS' : one.status === CANNOT_RUN ? 'SKIP' : 'FAIL'} ${one.gate}`);
  }
  if (skipped.length > 0) console.log('INCOMPLETE: a gate could not run, and this tree treats a skip as a failure');
  return failed.length + skipped.length === 0 ? PASS : 1;
}

if (import.meta.main) process.exitCode = sweep();
