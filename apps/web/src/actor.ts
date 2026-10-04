import type { Actor, Agent } from './api/types';
import { roleName } from './roles.ts';

const STAGE: Record<Agent, string> = {
  vigia: 'detección',
  analista: 'análisis',
  estratega: 'propuesta',
  ejecutor: 'ejecución',
  chat: 'chat',
};

export function agentName(agent: Agent): string {
  return `Centinela · ${STAGE[agent]}`;
}

export function who(actor: Actor): string {
  return actor.kind === 'agent' ? agentName(actor.agent) : `${actor.name} (${roleName(actor.role)})`;
}
