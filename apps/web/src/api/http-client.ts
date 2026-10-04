import { messageOfError } from './error-message';
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
} from './types';

export const STATUS_ESTADO: Record<Exclude<AlertStatus, 'merged'>, string> = {
  new: 'nueva',
  analyzing: 'en_analisis',
  proposed: 'propuesta',
  approved: 'aprobada',
  rejected: 'rechazada',
  executed: 'ejecutada',
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
  const response = await fetch(url, {
    ...options,
    headers: { ...(anonymous ? API_HEADERS : authHeaders()), ...options?.headers },
  });

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

export async function getSimulatedDay(): Promise<string> {
  const day = await fetchJson<{ dia: string }>(`${API_BASE_URL}/simulacion/dia-actual`);
  return day.dia;
}

export async function* advanceDay(days = 1): AsyncGenerator<AdvanceEvent> {
  const response = await request(`${API_BASE_URL}/simulacion/avanzar?dias=${days}`, { method: 'POST' });

  if (!response.body) {
    throw new Error('No response body');
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
  if (filter.status && filter.status !== 'merged') {
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
        : { kind: 'reject', reason: decision.reason };

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
    throw new Error('No response body');
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
  return {
    metrics: [
      {
        metric: 'margen_pct',
        name: 'Margen porcentual',
        description: 'Margen bruto sobre ventas por línea de producto',
        view: 'v_margen_semanal_linea',
        rule: 'Alerta si cae más de X puntos vs. promedio 4 semanas',
        threshold: { value: 3, label: 'Caída máxima en puntos porcentuales' },
        watched: true,
        owner: 'Gerente Comercial',
      },
      {
        metric: 'saldo_vencido',
        name: 'Saldo vencido',
        description: 'Cartera vencida de clientes en COP',
        view: 'v_cartera_cliente',
        rule: 'Alerta si supera X% del saldo total por cliente',
        threshold: { value: 20, label: 'Porcentaje máximo de cartera vencida' },
        watched: true,
        owner: 'Gerente Financiero',
      },
      {
        metric: 'dias_pago_prom',
        name: 'Días promedio de pago',
        description: 'Promedio de días que tarda un cliente en pagar',
        view: 'v_dias_pago_mensual',
        rule: 'Alerta si supera X días vs. política de crédito',
        threshold: { value: 45, label: 'Días máximos de pago' },
        watched: true,
        owner: 'Gerente Financiero',
      },
      {
        metric: 'cobertura_dias',
        name: 'Cobertura en días',
        description: 'Días de inventario disponible por producto',
        view: 'v_cobertura_inventario',
        rule: 'Alerta si baja de X días de cobertura',
        threshold: { value: 15, label: 'Días mínimos de cobertura' },
        watched: true,
        owner: 'Gerente de Operaciones',
      },
      {
        metric: 'descuento_en_exceso',
        name: 'Descuento en exceso',
        description: 'Descuentos aplicados fuera de política comercial',
        view: 'v_descuentos_fuera_politica',
        rule: 'Alerta si el descuento supera X% sobre la política',
        threshold: { value: 5, label: 'Puntos porcentuales sobre política' },
        watched: false,
        owner: 'Gerente Comercial',
      },
      {
        metric: 'veces_intervalo_habitual',
        name: 'Actividad inusual de cliente',
        description: 'Compras fuera del intervalo habitual del cliente',
        view: 'v_actividad_cliente',
        rule: 'Alerta si el intervalo supera X veces el habitual',
        threshold: { value: 2, label: 'Veces el intervalo habitual' },
        watched: false,
        owner: 'Gerente Comercial',
      },
    ],
    owners: ['Gerente Comercial', 'Gerente Financiero', 'Gerente de Operaciones'],
    autonomy: {
      email_draft: 'propose',
      task: 'propose',
      purchase_order_draft: 'propose',
      price_change_draft: 'propose',
    },
  };
}

export async function saveSettings(next: Settings): Promise<Settings> {
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

export async function getQuery(id: string): Promise<Query> {
  return fetchJson<Query>(`${API_BASE_URL}/consultas/${encodeURIComponent(id)}`);
}
