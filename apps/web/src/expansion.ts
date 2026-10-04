import type { TreeExpansion } from './api/types';

const INACTIVE: Record<NonNullable<TreeExpansion['inactiveReason']>, string> = {
  dropped_by_base: 'Un cambio más reciente del árbol ya cubre este y lo dejó sin efecto.',
  parent_retired: 'Se retiró el cambio del que dependía, así que ya no se aplica.',
};

export function inactiveLine(reason: TreeExpansion['inactiveReason']): string {
  return reason === null ? 'Ya no se aplica.' : INACTIVE[reason];
}
