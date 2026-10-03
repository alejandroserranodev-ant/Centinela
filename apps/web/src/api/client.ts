import { parameterName } from '../actionParameters';
import { formatDate, formatFigureInText } from '../format';
import alertsJson from './fixtures/alerts.json';
import chatJson from './fixtures/chat.json';
import clockJson from './fixtures/clock.json';
import queriesJson from './fixtures/queries.json';
import settingsJson from './fixtures/settings.json';
import type {
  Action,
  ActionType,
  Actor,
  AdvanceEvent,
  Agent,
  AgentStep,
  Alert,
  AlertFilter,
  Cause,
  ChatEvent,
  ChatMessage,
  ChatQuestion,
  Decision,
  Figure,
  InboxSummary,
  LogEvent,
  LogFilter,
  Query,
  Sentence,
  SeriesPoint,
  Settings,
  SimulationState,
  User,
} from './types';

type AlertFixture = Omit<Alert, 'status' | 'executedAction'> & {
  script: Record<'analista' | 'estratega', string>;
};

interface ChatAnswer {
  id: string;
  alertId: string | null;
  keywords: string[];
  text: string;
  figures: Figure[];
  series?: SeriesPoint[];
  enoughEvidence: boolean;
}

interface ChatFixture {
  answers: ChatAnswer[];
  noEvidence: Omit<ChatAnswer, 'id' | 'alertId' | 'keywords'>;
}

interface ClockFixture {
  initialDay: string;
  user: User;
}

export class ApiError extends Error {
  constructor(
    readonly status: 404 | 409 | 422,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const STEP_DELAY_MS = 900;
const CHUNK_DELAY_MS = 45;

const RESULT_BY_TYPE: Record<ActionType, string> = {
  email_draft: 'Borrador de correo guardado; queda sin enviar hasta que una persona lo envíe',
  task: 'Tarea creada y asignada',
  purchase_order_draft: 'Borrador de orden de compra guardado; queda sin emitir',
  price_change_draft: 'Borrador de ajuste de precio guardado; la lista de precios no cambia hasta publicarlo',
};

const clock = clockJson as ClockFixture;
const fixtures = (alertsJson as unknown as AlertFixture[]).map(resolveAlert);
const queries = new Map((queriesJson as Query[]).map((q) => [q.id, q]));
const chatAnswers = chatJson as unknown as ChatFixture;
let currentSettings = settingsJson as Settings;

let simulatedDay = clock.initialDay;
const alerts = new Map<string, Alert>();
const logEvents: LogEvent[] = [];
const changesRequested = new Set<string>();
let sequence = 0;

for (const fixture of fixtures.filter((f) => f.simulatedDate <= simulatedDay)) {
  const alert = createAlert(fixture, 'proposed');
  logDetection(alert);
  logAnalysis(alert);
  logProposal(alert);
}

export async function getSimulationState(): Promise<SimulationState> {
  return { simulatedDay, user: { ...clock.user } };
}

export async function* advanceDay(days = 1): AsyncGenerator<AdvanceEvent> {
  const newAlerts: string[] = [];
  for (let i = 0; i < days; i++) {
    simulatedDay = addDays(simulatedDay, 1);
    const ofTheDay = fixtures.filter((f) => f.simulatedDate === simulatedDay);

    const vigia = startStep(null, 'vigia', `Revisando los indicadores del ${formatDate(simulatedDay)}`);
    yield { event: 'step', data: { ...vigia } };
    await wait(STEP_DELAY_MS);
    finishStep(
      vigia,
      ofTheDay.length === 0
        ? 'Sin hallazgos: todos los indicadores están dentro de sus umbrales'
        : `Encontré algo que decidir: ${ofTheDay.map((f) => f.title.text).join('; ')}`,
    );
    yield { event: 'step', data: { ...vigia } };

    for (const fixture of ofTheDay) {
      const alert = createAlert(fixture, 'new');
      newAlerts.push(alert.id);
      logDetection(alert);
      yield { event: 'alert', data: copy(alert) };

      alert.status = 'analyzing';
      const analista = startStep(alert.id, 'analista', fixture.script.analista);
      yield { event: 'step', data: { ...analista } };
      yield { event: 'alert', data: copy(alert) };
      await wait(STEP_DELAY_MS);
      logAnalysis(alert);
      finishStep(analista, fixture.cause.kind === 'identified' ? 'Causa identificada' : 'Sin evidencia suficiente para una causa');
      yield { event: 'step', data: { ...analista } };

      const estratega = startStep(alert.id, 'estratega', fixture.script.estratega);
      yield { event: 'step', data: { ...estratega } };
      await wait(STEP_DELAY_MS);
      alert.status = 'proposed';
      logProposal(alert);
      finishStep(estratega, 'Propuesta lista para decidir');
      yield { event: 'step', data: { ...estratega } };
      yield { event: 'alert', data: copy(alert) };
    }
  }
  yield { event: 'end', data: { simulatedDay, newAlerts } };
}

export async function listAlerts(filter: AlertFilter = {}): Promise<Alert[]> {
  return [...alerts.values()]
    .filter((a) => !filter.status || a.status === filter.status)
    .sort((a, b) => b.pesosAtRisk.value - a.pesosAtRisk.value)
    .map(copy);
}

export async function getAlert(id: string): Promise<Alert> {
  return copy(findAlert(id));
}

export async function decide(id: string, decision: Decision): Promise<Alert> {
  const alert = findAlert(id);
  if (alert.status !== 'proposed') {
    throw new ApiError(409, 'Esta alerta ya no espera una decisión');
  }
  const person: Actor = { kind: 'person', ...clock.user };

  if (decision.kind === 'reject') {
    const reason = decision.reason.trim();
    if (!reason) {
      throw new ApiError(422, 'Para rechazar hace falta un motivo');
    }
    alert.status = 'rejected';
    log(alert.id, 'decision', person, `Rechazada. Motivo: ${reason}`);
    return copy(alert);
  }

  if (decision.kind === 'request_changes') {
    const reason = decision.reason.trim();
    if (!reason) {
      throw new ApiError(422, 'Para pedir cambios hace falta un motivo');
    }
    if (changesRequested.has(alert.id)) {
      throw new ApiError(422, 'Esta alerta ya pidió cambios una vez');
    }
    changesRequested.add(alert.id);
    log(alert.id, 'decision', person, `Cambios solicitados. Motivo: ${reason}`);
    await wait(STEP_DELAY_MS);
    log(alert.id, 'proposal', { kind: 'agent', agent: 'estratega' }, `Propuesta revisada con el motivo: ${reason}`);
    return copy(alert);
  }

  const action = alert.actions.find((a) => a.id === decision.actionId);
  if (!action) {
    throw new ApiError(422, 'La acción elegida no pertenece a esta alerta');
  }
  if (decision.kind === 'edit') {
    action.parameters = { ...action.parameters, ...decision.parameters };
  }
  alert.status = 'approved';
  log(alert.id, 'decision', person, describeApproval(action, decision));

  await wait(STEP_DELAY_MS);
  const ejecutor: Actor = { kind: 'agent', agent: 'ejecutor' };
  const actionDetail =
    decision.kind === 'edit'
      ? `${action.title}, con ${describeParameters(decision.parameters)}`
      : `${action.title}: ${action.description.text}`;
  log(alert.id, 'action', ejecutor, actionDetail);
  const result = RESULT_BY_TYPE[action.type];
  alert.status = 'executed';
  alert.executedAction = { actionId: action.id, result };
  log(alert.id, 'result', ejecutor, result);
  return copy(alert);
}

export async function* chat({ question, alertId }: ChatQuestion): AsyncGenerator<ChatEvent> {
  const answer = pickAnswer(question, alertId);
  const step = startStep(alertId ?? null, 'analista', 'Buscando la respuesta en los datos');
  yield { event: 'step', data: { ...step } };
  await wait(STEP_DELAY_MS);
  finishStep(step, answer.enoughEvidence ? 'Respuesta encontrada' : 'Sin evidencia suficiente');
  yield { event: 'step', data: { ...step } };

  const text = fillIn(answer.text, answer.figures);
  for (const chunk of text.split(/(?<=\s)/)) {
    await wait(CHUNK_DELAY_MS);
    yield { event: 'chunk', data: { text: chunk } };
  }

  const message: ChatMessage = {
    id: nextId('msg'),
    role: 'centinela',
    text,
    figures: structuredClone(answer.figures),
    enoughEvidence: answer.enoughEvidence,
    date: new Date().toISOString(),
    ...(alertId ? { alertId } : {}),
    ...(answer.series ? { series: structuredClone(answer.series) } : {}),
  };
  yield { event: 'end', data: message };
}

export async function getInboxSummary(): Promise<InboxSummary> {
  const pending = [...alerts.values()].filter((a) => a.status === 'proposed');
  return {
    moneyAtRisk: {
      value: pending.reduce((sum, a) => sum + a.pesosAtRisk.value, 0),
      unit: 'COP',
      queryId: 'q-summary-risk',
    },
    pendingDecisions: { value: pending.length, unit: 'units', queryId: 'q-summary-pending' },
    recoverablePerMonth: {
      value: pending.reduce((sum, a) => sum + (a.recoverablePerMonth?.value ?? 0), 0),
      unit: 'COP',
      queryId: 'q-summary-recoverable',
    },
  };
}

export async function getSettings(): Promise<Settings> {
  return structuredClone(currentSettings);
}

export async function saveSettings(next: Settings): Promise<Settings> {
  if (Object.values(next.autonomy).some((level) => level === 'execute')) {
    throw new ApiError(422, 'Ninguna acción puede ejecutarse sola durante el piloto: el máximo es Propone');
  }
  currentSettings = structuredClone(next);
  return structuredClone(currentSettings);
}

export async function listBitacora(filter: LogFilter = {}): Promise<LogEvent[]> {
  return logEvents
    .filter((e) => (!filter.alertId || e.alertId === filter.alertId) && (!filter.type || e.type === filter.type))
    .reverse()
    .map((e) => structuredClone(e));
}

export async function getQuery(id: string): Promise<Query> {
  const found = queries.get(id);
  if (!found) {
    throw new ApiError(404, 'No existe esa consulta');
  }
  return { ...found };
}

function createAlert(fixture: AlertFixture, status: Alert['status']): Alert {
  const { script: _script, ...data } = structuredClone(fixture);
  const alert: Alert = { ...data, status };
  alerts.set(alert.id, alert);
  return alert;
}

function findAlert(id: string): Alert {
  const alert = alerts.get(id);
  if (!alert) {
    throw new ApiError(404, 'No existe esa alerta');
  }
  return alert;
}

function logDetection(alert: Alert) {
  log(alert.id, 'alert', { kind: 'agent', agent: 'vigia' }, alert.title.text, alert.title.figures[0]?.queryId);
}

function logAnalysis(alert: Alert) {
  const analista: Actor = { kind: 'agent', agent: 'analista' };
  if (alert.cause.kind === 'no_evidence') {
    log(alert.id, 'evidence', analista, alert.cause.reason);
    return;
  }
  for (const evidence of alert.cause.evidence) {
    log(alert.id, 'evidence', analista, evidence.claim.text, evidence.queryId);
  }
}

function logProposal(alert: Alert) {
  const titles = alert.actions.map((a) => a.title).join('; ');
  log(alert.id, 'proposal', { kind: 'agent', agent: 'estratega' }, titles);
}

function log(alertId: string, type: LogEvent['type'], actor: Actor, detail: string, queryId?: string) {
  logEvents.push({
    id: nextId('ev'),
    date: new Date().toISOString(),
    simulatedDay,
    alertId,
    type,
    actor,
    detail,
    ...(queryId ? { queryId } : {}),
  });
}

function describeApproval(action: Action, decision: Decision): string {
  if (decision.kind !== 'edit') {
    return `Aprobada: ${action.title}`;
  }
  return `Aprobada con cambios: ${action.title} (${describeParameters(decision.parameters)})`;
}

function describeParameters(parameters: Record<string, string | number>): string {
  return Object.entries(parameters)
    .map(([key, value]) => `${parameterName(key)}: ${value}`)
    .join(', ');
}

function startStep(alertId: string | null, agent: Agent, description: string): AgentStep {
  return { alertId, agent, status: 'running', description, start: new Date().toISOString() };
}

function finishStep(step: AgentStep, description: string) {
  step.status = 'done';
  step.description = description;
  step.end = new Date().toISOString();
}

function pickAnswer(question: string, alertId?: string): Omit<ChatAnswer, 'id' | 'alertId' | 'keywords'> {
  const text = normalize(question);
  const candidates = chatAnswers.answers.filter(
    (a) => (a.alertId === null || a.alertId === alertId) && a.keywords.every((k) => text.includes(normalize(k))),
  );
  return candidates.find((a) => a.alertId !== null) ?? candidates[0] ?? chatAnswers.noEvidence;
}

function normalize(text: string): string {
  return text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

function resolveAlert(fixture: AlertFixture): AlertFixture {
  return {
    ...fixture,
    title: resolveSentence(fixture.title),
    cause: resolveCause(fixture.cause),
    actions: fixture.actions.map((a) => ({ ...a, description: resolveSentence(a.description) })) as Alert['actions'],
    mergedAlerts: fixture.mergedAlerts?.map((m) => ({ ...m, title: resolveSentence(m.title), cause: resolveCause(m.cause) })),
  };
}

function resolveCause(cause: Cause): Cause {
  return cause.kind === 'identified'
    ? {
        ...cause,
        sentence: resolveSentence(cause.sentence),
        evidence: cause.evidence.map((e) => ({ ...e, claim: resolveSentence(e.claim) })),
      }
    : cause;
}

function resolveSentence(sentence: Sentence): Sentence {
  return { ...sentence, text: fillIn(sentence.text, sentence.figures) };
}

function fillIn(text: string, figures: Figure[]): string {
  return text.replace(/\{(\d+)\}/g, (marker, index: string) => {
    const figure = figures[Number(index)];
    return figure ? formatFigureInText(figure) : marker;
  });
}

function addDays(day: string, n: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function nextId(prefix: string): string {
  sequence += 1;
  return `${prefix}-${sequence}`;
}

function copy(alert: Alert): Alert {
  return structuredClone(alert);
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
