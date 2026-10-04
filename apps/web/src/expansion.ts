import type { TreeExpansion } from './api/types';

const INACTIVE: Record<NonNullable<TreeExpansion['inactiveReason']>, string> = {
  dropped_by_base: 'El árbol de base o sus reglas cambiaron y este cambio ya no las cumple, así que dejó de aplicarse.',
  parent_retired: 'Se retiró el cambio del que dependía, así que ya no se aplica.',
};

export function inactiveLine(reason: TreeExpansion['inactiveReason']): string {
  return reason === null ? 'Ya no se aplica.' : INACTIVE[reason];
}
