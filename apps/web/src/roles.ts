import type { Persona } from './api/types';

const ROLE: Record<Persona['role'], string> = {
  gerente: 'Gerente',
  lider_proceso: 'Líder de proceso',
  analista: 'Analista',
  auditor: 'Auditoría',
};

export function roleName(role: string): string {
  return ROLE[role as Persona['role']] ?? role;
}

export function roleLabel(persona: Pick<Persona, 'role' | 'area'>): string {
  const label = roleName(persona.role);
  return persona.role === 'lider_proceso' && persona.area ? `${label} · ${persona.area}` : label;
}

export function canConfigure(persona: Pick<Persona, 'role'>): boolean {
  return persona.role === 'analista' || persona.role === 'gerente';
}
