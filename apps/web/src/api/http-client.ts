import { messageOfError, OFFLINE, reach } from './error-message';
import { API_BASE_URL, API_HEADERS, authHeaders } from './config';
import { getToken, notifyUnauthorized } from './session';
import { readSse } from './sse';
import type {
  AdvanceEvent,
  AgentStep,
  Alert,
  AlertFilter,
  AlertStatus,
  ChatEvent,
  ChatMessage,
  ChatQuestion,
  Decision,
  InboxSummary,
  LogEvent,
  LogFilter,
  Query,
  Persona,
  Session,
  Settings,
  SimulatedDay,
  TreeExpansion,
} from './types';

export const STATUS_ESTADO: Record<AlertStatus, string> = {
  new: 'nueva',
  analyzing: 'en_analisis',
  proposed: 'propuesta',
  approved: 'aprobada',
  rejected: 'rechazada',
  executed: 'ejecutada',
  merged: 'unida',
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function errorMessage(response: Response): Promise<string> {
  const text = await response.text().catch(() => '');
  return messageOfError(text, response.statusText);
}

async function request(url: string, options?: RequestInit, anonymous = false): Promise<Response> {
  const sent = getToken();
  const response = await reach(
    () => fetch(url, { ...options, headers: { ...(anonymous ? API_HEADERS : authHeaders()), ...options?.headers } }),
    (message) => new ApiError(0, message),
  );

  if (!response.ok) {
    const message = await errorMessage(response);
    if (response.status === 401 && !anonymous) {
      notifyUnauthorized(sent);
    }
    throw new ApiError(response.status, message);
  }

  return response;
}

async function fetchJson<T>(url: string, options?: RequestInit, anonymous = false): Promise<T> {
  const response = await request(url, options, anonymous);
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<Session> {
  return fetchJson<Session>(
    `${API_BASE_URL}/auth/login`,
    { method: 'POST', body: JSON.stringify({ email, password }) },
    true,
  );
}

export async function getSession(): Promise<Persona> {
  return fetchJson<Persona>(`${API_BASE_URL}/auth/sesion`);
}

export async function getSimulatedDay(): Promise<SimulatedDay> {
  return fetchJson<SimulatedDay>(`${API_BASE_URL}/simulacion/dia-actual`);
}

export async function* advanceDay(days = 1): AsyncGenerator<AdvanceEvent> {
  const response = await request(`${API_BASE_URL}/simulacion/avanzar?dias=${days}`, { method: 'POST' });

  if (!response.body) {
    throw new ApiError(0, OFFLINE);
  }

  for await (const { event, data } of readSse(response.body)) {
    if (event === 'step') {
      yield { event: 'step', data: data as AgentStep };
    } else if (event === 'alert') {
      yield { event: 'alert', data: data as Alert };
    } else if (event === 'end') {
      yield { event: 'end', data: data as { simulatedDay: string; newAlerts: string[] } };
    }
  }
}

export async function listAlerts(filter: AlertFilter = {}): Promise<Alert[]> {
  const params = new URLSearchParams();
  if (filter.status) {
    params.set('estado', STATUS_ESTADO[filter.status]);
  }

  const url = new URL(`${API_BASE_URL}/alertas`);
  url.search = params.toString();
  return fetchJson<Alert[]>(url.toString());
}

export async function getAlert(id: string): Promise<Alert> {
  return fetchJson<Alert>(`${API_BASE_URL}/alertas/${id}`);
}

export async function decide(id: string, decision: Decision): Promise<Alert> {
  const payload =
    decision.kind === 'edit'
      ? { kind: 'edit', actionId: decision.actionId, parameters: decision.parameters }
      : decision.kind === 'approve'
        ? { kind: 'approve', actionId: decision.actionId }
        : { kind: decision.kind, reason: decision.reason };

  return fetchJson<Alert>(`${API_BASE_URL}/alertas/${id}/decision`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function* chat({ question, alertId }: ChatQuestion): AsyncGenerator<ChatEvent> {
  const response = await request(`${API_BASE_URL}/chat`, {
    method: 'POST',
    body: JSON.stringify({ question, alertId }),
  });

  if (!response.body) {
    throw new ApiError(0, OFFLINE);
  }

  for await (const { event, data } of readSse(response.body)) {
    if (event === 'step') {
      yield { event: 'step', data: data as AgentStep };
    } else if (event === 'end') {
      yield { event: 'end', data: data as ChatMessage };
    }
  }
}

export async function getInboxSummary(): Promise<InboxSummary> {
  return fetchJson<InboxSummary>(`${API_BASE_URL}/bandeja/resumen`);
}

export async function getSettings(): Promise<Settings> {
  return fetchJson<Settings>(`${API_BASE_URL}/configuracion`);
}

export async function saveSettings(next: Settings): Promise<Settings> {
  return fetchJson<Settings>(`${API_BASE_URL}/configuracion`, { method: 'PUT', body: JSON.stringify(next) });
}

export async function listExpansions(): Promise<TreeExpansion[]> {
  return fetchJson<TreeExpansion[]>(`${API_BASE_URL}/arbol/expansiones`);
}

export async function retireExpansion(id: string, reason: string): Promise<TreeExpansion> {
  return fetchJson<TreeExpansion>(`${API_BASE_URL}/arbol/expansiones/${encodeURIComponent(id)}/retiro`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function listBitacora(filter: LogFilter = {}): Promise<LogEvent[]> {
  const params = new URLSearchParams();
  if (filter.alertId) params.set('alertId', filter.alertId);
  if (filter.type) params.set('type', filter.type);

  const url = new URL(`${API_BASE_URL}/bitacora`);
  url.search = params.toString();
  return fetchJson<LogEvent[]>(url.toString());
}

export async function getQuery(id: string): Promise<Query> {
  return fetchJson<Query>(`${API_BASE_URL}/consultas/${encodeURIComponent(id)}`);
}
