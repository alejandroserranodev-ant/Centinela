import { ArenaTag } from '@dravensoft/arena-react';
import type { AlertStatus, ConfidenceLevel, Severity as SeverityLevel } from '../api/types';

const SEVERITY: Record<SeverityLevel, string> = {
  critical: 'Crítica',
  high: 'Alta',
  medium: 'Media',
  low: 'Baja',
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
  return (
    <span className={`severity severity--${level}`}>
      {level === 'critical' ? <i className="ph-fill ph-warning" aria-hidden /> : null}
      {SEVERITY[level]}
    </span>
  );
}

export function Confidence({ level }: { level: ConfidenceLevel }) {
  return <ArenaTag>{CONFIDENCE[level]}</ArenaTag>;
}

export function Status({ status }: { status: AlertStatus }) {
  const tone = status === 'approved' || status === 'executed' ? 'success' : 'neutral';
  return <ArenaTag tone={tone}>{STATUS[status]}</ArenaTag>;
}
