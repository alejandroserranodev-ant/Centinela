import type { Cause } from './api/types';

export function explainedByRemaining(cause: Pick<Cause, 'kind'>, merged: boolean): boolean {
  return merged && cause.kind === 'no_evidence';
}
