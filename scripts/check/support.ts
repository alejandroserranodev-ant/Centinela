import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';

export type Planted = Record<string, string | { symlink: string }>;

export function plant(files: Planted): string {
  const root = mkdtempSync(join(tmpdir(), 'centinela-check-'));
  execFileSync('git', ['init', '-q'], { cwd: root });
  for (const [path, content] of Object.entries(files)) {
    mkdirSync(dirname(join(root, path)), { recursive: true });
    if (typeof content === 'string') writeFileSync(join(root, path), content);
    else symlinkSync(content.symlink, join(root, path));
  }
  return root;
}

export const ROUTER = '# Router\n\n| I am here because | Start at |\n|---|---|\n| a thing | [`a/AGENTS.md`](./a/AGENTS.md) |\n';
