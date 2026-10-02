export type AlertStatus = 'new' | 'analyzing' | 'proposed' | 'approved' | 'rejected' | 'executed' | 'merged';

export type Severity = 'critical' | 'high' | 'medium' | 'low';

export type ConfidenceLevel = 'high' | 'medium' | 'low';

export type Metric =
  | 'margen_pct'
  | 'saldo_vencido'
  | 'dias_pago_prom'
  | 'cobertura_dias'
  | 'descuento_en_exceso'
  | 'veces_intervalo_habitual';

export type SemanticView =
  | 'v_ventas'
  | 'v_margen_semanal_linea'
  | 'v_cartera_cliente'
  | 'v_dias_pago_mensual'
  | 'v_cobertura_inventario'
  | 'v_descuentos_fuera_politica'
  | 'v_actividad_cliente';

export type QuerySource = SemanticView | 'alertas';

export interface Query {
  id: string;
  source: QuerySource;
  sql: string;
  description: string;
}

export type FigureUnit = 'COP' | 'points' | 'percent' | 'days' | 'units';

export interface Figure {
  value: number;
  unit: FigureUnit;
  queryId: string;
}

export interface Sentence {
  text: string;
  figures: Figure[];
}

export interface Confidence {
  level: ConfidenceLevel;
  assumptions: string[];
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export interface Evidence {
  claim: Sentence;
  queryId: string;
  series?: SeriesPoint[];
}

export type Cause =
  | { kind: 'identified'; sentence: Sentence; evidence: Evidence[] }
  | { kind: 'no_evidence'; reason: string; queriesReviewed: string[] };

export type ActionType = 'email_draft' | 'task' | 'purchase_order_draft' | 'price_change_draft';

export interface Impact {
  figure: Figure;
  period: 'month' | 'once';
}

export interface Action {
  id: string;
  title: string;
  description: Sentence;
  type: ActionType;
  impact: Impact | null;
  confidence: Confidence;
  parameters: Record<string, string | number>;
}

export type Actions = [Action] | [Action, Action] | [Action, Action, Action];

export interface ExecutedAction {
  actionId: string;
  result: string;
}

export interface Alert {
  id: string;
  status: AlertStatus;
  severity: Severity;
  metric: Metric;
  title: Sentence;
  pesosAtRisk: Figure;
  recoverablePerMonth: Figure | null;
  confidence: Confidence;
  simulatedDate: string;
  cause: Cause;
  actions: Actions;
  executedAction?: ExecutedAction;
  mergedInto?: string;
}

export type Agent = 'vigia' | 'analista' | 'estratega' | 'ejecutor';

export interface AgentStep {
  alertId: string | null;
  agent: Agent;
  status: 'running' | 'done';
  description: string;
  start: string;
  end?: string;
}

export interface User {
  name: string;
  role: string;
}

export type Actor = { kind: 'agent'; agent: Agent } | ({ kind: 'person' } & User);

export type LogEventType = 'alert' | 'evidence' | 'proposal' | 'decision' | 'action' | 'result';

export interface LogEvent {
  id: string;
  date: string;
  simulatedDay: string;
  alertId: string;
  type: LogEventType;
  actor: Actor;
  detail: string;
  queryId?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'centinela';
  text: string;
  figures: Figure[];
  alertId?: string;
  series?: SeriesPoint[];
  enoughEvidence: boolean;
  date: string;
}

export interface SseEvent<E extends string, D> {
  event: E;
  data: D;
}

export type AdvanceEvent =
  | SseEvent<'step', AgentStep>
  | SseEvent<'alert', Alert>
  | SseEvent<'end', { simulatedDay: string; newAlerts: string[] }>;

export type ChatEvent =
  | SseEvent<'step', AgentStep>
  | SseEvent<'chunk', { text: string }>
  | SseEvent<'end', ChatMessage>;

export type Decision =
  | { kind: 'approve'; actionId: string }
  | { kind: 'edit'; actionId: string; parameters: Record<string, string | number> }
  | { kind: 'reject'; reason: string };

export interface ChatQuestion {
  question: string;
  alertId?: string;
}

export interface AlertFilter {
  status?: AlertStatus;
}

export interface LogFilter {
  alertId?: string;
  type?: LogEventType;
}

export interface SimulationState {
  simulatedDay: string;
  user: User;
}

export interface InboxSummary {
  moneyAtRisk: Figure;
  pendingDecisions: Figure;
  recoverablePerMonth: Figure;
}

export type AutonomyLevel = 'inform' | 'propose' | 'execute';

export interface Threshold {
  value: number;
  label: string;
}

export interface WatchedMetric {
  metric: Metric;
  name: string;
  description: string;
  view: SemanticView;
  rule: string;
  threshold: Threshold;
  watched: boolean;
  owner: string;
}

export interface Settings {
  metrics: WatchedMetric[];
  owners: string[];
  autonomy: Record<ActionType, AutonomyLevel>;
}
