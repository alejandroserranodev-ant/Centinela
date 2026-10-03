export const PASS = 0;
export const FAIL = 1;
export const CANNOT_RUN = 2;

export class CannotRun extends Error {}

export function zeroScanProblems(what: string, count: number): string[] {
  return count === 0 ? [`walked 0 ${what}, so every rule below passes over a tree it never opened`] : [];
}

export function staleProblems(name: string, map: Map<string, unknown>, holds: (key: string) => boolean): string[] {
  return [...map.keys()]
    .filter((key) => !holds(key))
    .map((key) => `${name} names ${key}, which the tree no longer holds`);
}

export function runGate(problems: () => string[]): void {
  try {
    const found = problems();
    for (const one of found) console.error(one);
    process.exitCode = found.length === 0 ? PASS : FAIL;
  } catch (error) {
    if (error instanceof CannotRun) {
      console.error(`SKIP: ${error.message}`);
      process.exitCode = CANNOT_RUN;
      return;
    }
    throw error;
  }
}
