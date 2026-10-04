import type { LogEvent, LogEventType } from './api/types';

const WITHOUT_ALERT: Partial<Record<LogEventType, string>> = {
  configuracion: 'Configuración',
  question: 'Chat, sin alerta',
  answer: 'Chat, sin alerta',
  refusal: 'Chat, sin alerta',
  arbol: 'Árbol de decisión',
};

export function withoutAlert(type: LogEventType): string {
  return WITHOUT_ALERT[type] ?? 'Sin alerta';
}

export function latestResult(events: LogEvent[]): LogEvent | null {
  return events.find((e) => e.type === 'result') ?? null;
}
