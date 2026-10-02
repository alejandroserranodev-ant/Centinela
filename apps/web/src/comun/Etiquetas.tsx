import { ArenaBadge, ArenaTag } from '@dravensoft/arena-react';
import type { ArenaTone } from '@dravensoft/arena-react';
import type { EstadoAlerta, NivelConfianza, Severidad as NivelSeveridad } from '../api/types';

const SEVERIDAD: Record<NivelSeveridad, { texto: string; tono: ArenaTone }> = {
  critica: { texto: 'Crítica', tono: 'danger' },
  alta: { texto: 'Alta', tono: 'warning' },
  media: { texto: 'Media', tono: 'info' },
  baja: { texto: 'Baja', tono: 'neutral' },
};

const CONFIANZA: Record<NivelConfianza, string> = {
  alta: 'Confianza alta',
  media: 'Confianza media',
  baja: 'Confianza baja',
};

export const ESTADO: Record<EstadoAlerta, string> = {
  nueva: 'Nueva',
  en_analisis: 'En análisis',
  propuesta: 'Por decidir',
  aprobada: 'Aprobada',
  rechazada: 'Rechazada',
  ejecutada: 'Ejecutada',
};

export function Severidad({ nivel }: { nivel: NivelSeveridad }) {
  const { texto, tono } = SEVERIDAD[nivel];
  return (
    <ArenaBadge tone={tono} dot>
      {texto}
    </ArenaBadge>
  );
}

export function Confianza({ nivel }: { nivel: NivelConfianza }) {
  return <ArenaTag>{CONFIANZA[nivel]}</ArenaTag>;
}

export function Estado({ estado }: { estado: EstadoAlerta }) {
  const tono = estado === 'aprobada' || estado === 'ejecutada' ? 'success' : 'neutral';
  return <ArenaTag tone={tono}>{ESTADO[estado]}</ArenaTag>;
}
