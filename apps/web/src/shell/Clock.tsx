import { ArenaButton, useArenaViewportBelow } from '@dravensoft/arena-react';
import { useSimulation } from '../state/Simulation';
import { formatDate, formatShortDate } from '../format';

export function Clock() {
  const { simulatedDay, advancing, advance } = useSimulation();
  const mobile = useArenaViewportBelow('sm');
  return (
    <div className="clock">
      <div className="clock__day">
        <span className="eyebrow">Día simulado</span>
        {simulatedDay ? (
          <time dateTime={simulatedDay}>{mobile ? formatShortDate(simulatedDay) : formatDate(simulatedDay)}</time>
        ) : null}
      </div>
      <span className="clock__button">
        <ArenaButton variant="secondary" size="sm" icon="ph-bold ph-fast-forward" loading={advancing} onClick={advance}>
          Avanzar un día
        </ArenaButton>
      </span>
    </div>
  );
}
