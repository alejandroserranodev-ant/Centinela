import { API_BASE_URL, API_HEADERS, getDecisionHeaders } from './config';
import type {
  AdvanceEvent,
  Alert,
  AlertFilter,
  ChatEvent,
  ChatMessage,
  ChatQuestion,
  Decision,
  InboxSummary,
  LogEvent,
  LogFilter,
  Query,
  Settings,
  SimulationState,
} from './types';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: { ...API_HEADERS, ...options?.headers },
  });

  if (!response.ok) {
    const error = await response.text().catch(() => response.statusText);
    throw new ApiError(response.status, error || response.statusText);
  }

  return response.json() as Promise<T>;
}

export async function getSimulationState(): Promise<SimulationState> {
  // Get current simulated day
  const dia = await fetchJson<{ dia: string }>(`${API_BASE_URL}/simulacion/dia-actual`);
  // For now, return the simulated day as both simulatedDay and user data
  // (User is hardcoded in config, real authentication would come later)
  return {
    simulatedDay: dia.dia,
    user: { name: 'Usuario Demo', role: 'gerente' },
  };
}

export async function* advanceDay(days = 1): AsyncGenerator<AdvanceEvent> {
  const response = await fetch(`${API_BASE_URL}/simulacion/avanzar?dias=${days}`, {
    method: 'POST',
    headers: API_HEADERS,
  });

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            const event = data.event as string;
            if (event === 'end') {
              yield {
                event: 'end',
                data: { simulatedDay: data.simulatedDay, newAlerts: data.newAlerts },
              };
            }
          } catch (e) {
            console.error('Failed to parse SSE event:', line, e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function listAlerts(filter: AlertFilter = {}): Promise<Alert[]> {
  const params = new URLSearchParams();
  if (filter.status) {
    // Convert status to Spanish for API
    const statusMap: Record<string, string> = {
      new: 'nueva',
      analyzing: 'en_analisis',
      proposed: 'propuesta',
      approved: 'aprobada',
      rejected: 'rechazada',
      executed: 'ejecutada',
    };
    params.set('estado', statusMap[filter.status]);
  }

  const url = new URL(`${API_BASE_URL}/alertas`);
  url.search = params.toString();
  return fetchJson<Alert[]>(url.toString());
}

export async function getAlert(id: string): Promise<Alert> {
  return fetchJson<Alert>(`${API_BASE_URL}/alertas/${id}`);
}

export async function decide(id: string, decision: Decision): Promise<Alert> {
  // Convert decision format if needed
  const payload =
    decision.kind === 'edit'
      ? { kind: 'edit', actionId: decision.actionId, parameters: decision.parameters }
      : decision.kind === 'approve'
        ? { kind: 'approve', actionId: decision.actionId }
        : { kind: 'reject', reason: decision.reason };

  return fetchJson<Alert>(`${API_BASE_URL}/alertas/${id}/decision`, {
    method: 'POST',
    headers: getDecisionHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function* chat({ question, alertId }: ChatQuestion): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: API_HEADERS,
    body: JSON.stringify({ question, alertId }),
  });

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            const event = data.event as string;
            if (event === 'step') {
              yield { event: 'step', data: data };
            } else if (event === 'end') {
              yield { event: 'end', data: data as ChatMessage };
            }
          } catch (e) {
            console.error('Failed to parse SSE event:', line, e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function getInboxSummary(): Promise<InboxSummary> {
  // Compute summary from alerts in 'proposed' status
  const alerts = await listAlerts({ status: 'proposed' });
  return {
    moneyAtRisk: {
      value: alerts.reduce((sum, a) => sum + a.pesosAtRisk.value, 0),
      unit: 'COP',
      queryId: 'q-summary-risk',
    },
    pendingDecisions: { value: alerts.length, unit: 'units', queryId: 'q-summary-pending' },
    recoverablePerMonth: {
      value: alerts.reduce((sum, a) => sum + (a.recoverablePerMonth?.value ?? 0), 0),
      unit: 'COP',
      queryId: 'q-summary-recoverable',
    },
  };
}

export async function getSettings(): Promise<Settings> {
  // For now, return hardcoded settings (not implemented in API yet)
  return {
    autonomy: {
      vigia: 'detects',
      analista: 'explains',
      estratega: 'proposes',
      ejecutor: 'proposes', // Never auto-executes during pilot
    },
  };
}

export async function saveSettings(next: Settings): Promise<Settings> {
  // Settings save not implemented in API yet
  if (Object.values(next.autonomy).some((level) => level === 'execute')) {
    throw new ApiError(422, 'Ninguna acción puede ejecutarse sola durante el piloto: el máximo es Propone');
  }
  return next;
}

export async function listBitacora(filter: LogFilter = {}): Promise<LogEvent[]> {
  const params = new URLSearchParams();
  if (filter.alertId) params.set('alertId', filter.alertId);
  if (filter.type) params.set('type', filter.type);

  const url = new URL(`${API_BASE_URL}/bitacora`);
  url.search = params.toString();
  return fetchJson<LogEvent[]>(url.toString());
}

export async function getQuery(_id: string): Promise<Query> {
  // Query storage not implemented in API yet
  throw new ApiError(404, 'No existe esa consulta');
}
