import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { CannotRun, runGate } from './gate.ts';
import { ROOT, present, read } from './tree.ts';

export const WEB = 'apps/web';
export const SCHEMA = `${WEB}/src/api/schema.generated.ts`;
export const OPENAPI = `${WEB}/src/api/openapi.json`;

export type Generate = (root: string, output: string) => string;

export function generator(root: string, output: string): string {
  const script = (JSON.parse(read(root, `${WEB}/package.json`)).scripts as Record<string, string>).contract;
  if (!script?.endsWith(` -o src/api/schema.generated.ts`)) {
    throw new CannotRun(`${WEB}/package.json declares no contract script that writes src/api/schema.generated.ts`);
  }
  const command = script.replace(/ -o src\/api\/schema\.generated\.ts$/, ` -o ${output}`);
  const run = spawnSync(command, { cwd: join(root, WEB), shell: true, encoding: 'utf8' });
  if (run.status !== 0) throw new CannotRun(`the contract generator failed: ${run.stderr || run.stdout}`);
  return output;
}

export function problems(root = ROOT, generate: Generate = generator): string[] {
  const missing = [OPENAPI, SCHEMA].filter((path) => !present(root, path));
  if (missing.length > 0) return missing.map((path) => `${path} is missing; run python -m centinela_api.contrato, then npm run contract in ${WEB}`);
  const scratch = mkdtempSync(join(tmpdir(), 'centinela-contract-'));
  try {
    const output = generate(root, join(scratch, 'schema.generated.ts'));
    return readFileSync(output, 'utf8') === read(root, SCHEMA)
      ? []
      : [`${SCHEMA} differs from what the generator writes from ${OPENAPI}; run npm run contract in ${WEB}`];
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
}

if (import.meta.main) runGate(() => problems());
