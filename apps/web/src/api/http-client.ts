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
