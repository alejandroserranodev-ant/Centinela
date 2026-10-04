import type { components } from './schema.generated.ts';

type Schemas = components['schemas'];

export type Alert = Schemas['Alert'];
export type AlertStatus = Alert['status'];
export type Severity = Alert['severity'];
export type Metric = Alert['metric'];
export type Cause = Alert['cause'];
export type MergedAlert = Schemas['MergedAlert'];
export type Figure = Schemas['Figure'];
export type FigureUnit = Figure['unit'];
export type Sentence = Schemas['Sentence-Output'];
export type Confidence = Schemas['Confidence-Output'];
export type ConfidenceLevel = Confidence['level'];
export type SeriesPoint = Schemas['SeriesPoint'];
export type Evidence = Schemas['Evidence-Output'];
export type Action = Schemas['Action-Output'];
export type ActionType = Action['type'];
export type Impact = Schemas['Impact'];
export type ExecutedAction = Schemas['ExecutedAction'];
export type AgentStep = Schemas['AgentStep'];
export type Agent = AgentStep['agent'];
export type Actor = LogEvent['actor'];
export type LogEvent = Schemas['LogEvent'];
export type LogEventType = LogEvent['type'];
export type ChatMessage = Schemas['ChatMessage'];
export type ChatOutcome = ChatMessage['outcome'];
export type ChatQuestion = Schemas['ChatQuestion'];
export type Query = Schemas['Query'];
export type Persona = Schemas['Persona'];
export type Session = Schemas['Sesion'];

export type QuerySource = SemanticView | Query['source'];
export type AdvanceEnd = Schemas['AdvanceEnd'];
export type ApiDecision = Schemas['DecisionApprove'] | Schemas['DecisionEdit'] | Schemas['DecisionReject'];

export type SemanticView =
  | 'v_ventas'
  | 'v_margen_semanal_linea'
  | 'v_cartera_cliente'
  | 'v_dias_pago_mensual'
  | 'v_cobertura_inventario'
  | 'v_descuentos_fuera_politica'
  | 'v_actividad_cliente';

export interface SseEvent<E extends string, D> {
  event: E;
  data: D;
}

export type AdvanceEvent =
  | SseEvent<'step', AgentStep>
  | SseEvent<'alert', Alert>
  | SseEvent<'end', AdvanceEnd>;

export type ChatEvent =
  | SseEvent<'step', AgentStep>
  | SseEvent<'end', ChatMessage>;

export type Decision = ApiDecision | { kind: 'request_changes'; reason: string };

export interface AlertFilter {
  status?: AlertStatus;
}

export interface LogFilter {
  alertId?: string;
  type?: LogEventType;
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
