import { ArenaProgressBar } from '@dravensoft/arena-react';
import type { Agente } from '../api/types';
import { useSimulacion } from '../estado/Simulacion';

const ETAPAS: Agente[] = ['vigia', 'analista', 'estratega'];

const NOMBRE_ETAPA: Record<Agente, string> = {
  vigia: 'Revisando los indicadores',
  analista: 'Explicando la causa',
  estratega: 'Preparando la propuesta',
  ejecutor: 'Ejecutando lo aprobado',
};

export function PasoEnCurso() {
  const { avanzando, paso } = useSimulacion();
  if (!avanzando || !paso) {
    return null;
  }
  const indice = Math.max(ETAPAS.indexOf(paso.agente), 0);
  const avance = ((indice + (paso.estado === 'hecho' ? 1 : 0.5)) / ETAPAS.length) * 100;
  return (
    <div className="paso-en-curso">
      <div className="arena-band arena-stack arena-stack--group paso-en-curso__cuerpo">
        <ArenaProgressBar
          size="sm"
          progressPercentage={avance}
          showPercentage={false}
          label={`Paso ${indice + 1} de ${ETAPAS.length}: ${NOMBRE_ETAPA[paso.agente]}`}
        />
        <p className="texto-tenue" aria-live="polite">
          {paso.descripcion}
        </p>
      </div>
    </div>
  );
}
