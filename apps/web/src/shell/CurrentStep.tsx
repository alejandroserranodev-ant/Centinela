import { ArenaProgressBar } from '@dravensoft/arena-react';
import type { Agent } from '../api/types';
import { useSimulation } from '../state/Simulation';

const STAGES: Agent[] = ['vigia', 'analista', 'estratega'];

const STAGE_NAME: Record<Agent, string> = {
  vigia: 'Revisando los indicadores',
  analista: 'Explicando la causa',
  estratega: 'Preparando la propuesta',
  ejecutor: 'Ejecutando lo aprobado',
  chat: 'Respondiendo una pregunta',
};

export function CurrentStep() {
  const { advancing, step } = useSimulation();
  if (!advancing || !step) {
    return null;
  }
  const index = Math.max(STAGES.indexOf(step.agent), 0);
  const progress = ((index + (step.status === 'done' ? 1 : 0.5)) / STAGES.length) * 100;
  return (
    <div className="current-step">
      <div className="arena-band arena-stack arena-stack--group current-step__body">
        <ArenaProgressBar
          size="sm"
          progressPercentage={progress}
          showPercentage={false}
          label={`Paso ${index + 1} de ${STAGES.length}: ${STAGE_NAME[step.agent]}`}
        />
        <p className="text-muted" aria-live="polite">
          {step.description}
        </p>
      </div>
    </div>
  );
}
