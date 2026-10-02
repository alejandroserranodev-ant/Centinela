import { ArenaBadge, ArenaTag } from '@dravensoft/arena-react';
import type { ArenaTone } from '@dravensoft/arena-react';
import type { AlertStatus, ConfidenceLevel, Severity as SeverityLevel } from '../api/types';

const SEVERITY: Record<SeverityLevel, { text: string; tone: ArenaTone }> = {
  critical: { text: 'Crítica', tone: 'danger' },
  high: { text: 'Alta', tone: 'warning' },
  medium: { text: 'Media', tone: 'info' },
  low: { text: 'Baja', tone: 'neutral' },
};

const CONFIDENCE: Record<ConfidenceLevel, string> = {
  high: 'Confianza alta',
  medium: 'Confianza media',
  low: 'Confianza baja',
};

export const STATUS: Record<AlertStatus, string> = {
  new: 'Nueva',
  analyzing: 'En análisis',
  proposed: 'Por decidir',
  approved: 'Aprobada',
  rejected: 'Rechazada',
  executed: 'Ejecutada',
  merged: 'Unida',
};

export function Severity({ level }: { level: SeverityLevel }) {
  const { text, tone } = SEVERITY[level];
  return (
    <ArenaBadge tone={tone} dot>
      {text}
    </ArenaBadge>
  );
}

export function Confidence({ level }: { level: ConfidenceLevel }) {
  return <ArenaTag>{CONFIDENCE[level]}</ArenaTag>;
}

export function Status({ status }: { status: AlertStatus }) {
  const tone = status === 'approved' || status === 'executed' ? 'success' : 'neutral';
  return <ArenaTag tone={tone}>{STATUS[status]}</ArenaTag>;
}
