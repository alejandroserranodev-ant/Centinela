import { ArenaButton, useArenaViewportBelow } from '@dravensoft/arena-react';
import { useSimulacion } from '../estado/Simulacion';
import { fecha, fechaCorta } from '../formato';

export function Reloj() {
  const { diaSimulado, avanzando, avanzar } = useSimulacion();
  const movil = useArenaViewportBelow('sm');
  return (
    <div className="reloj">
      <div className="reloj__dia">
        <span className="rotulo">Día simulado</span>
        {diaSimulado ? <time dateTime={diaSimulado}>{movil ? fechaCorta(diaSimulado) : fecha(diaSimulado)}</time> : null}
      </div>
      <span className="reloj__boton">
        <ArenaButton variant="secondary" size="sm" icon="ph-bold ph-fast-forward" loading={avanzando} onClick={avanzar}>
          Avanzar un día
        </ArenaButton>
      </span>
    </div>
  );
}
