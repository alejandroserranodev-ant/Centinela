import { useEffect, useState } from 'react';
import { ArenaButton, ArenaDialog, ArenaSkeleton } from '@dravensoft/arena-react';
import { consulta } from '../api/client';
import type { Consulta } from '../api/types';
import { useSimulacion } from '../estado/Simulacion';
import { BloqueConsulta } from './BloqueConsulta';

export function DialogoConsulta() {
  const { consultaAbierta, cerrarConsulta } = useSimulacion();
  const [datos, setDatos] = useState<Consulta | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setDatos(null);
    setError(false);
    if (consultaAbierta) {
      consulta(consultaAbierta).then(setDatos, () => setError(true));
    }
  }, [consultaAbierta]);

  return (
    <ArenaDialog
      open={consultaAbierta !== null}
      eyebrow="Cómo llegué aquí"
      title="De dónde sale esta cifra"
      width="calc(var(--sp-1) * 160)"
      fillBelow="sm"
      onClose={cerrarConsulta}
      footer={
        <ArenaButton variant="secondary" onClick={cerrarConsulta}>
          Cerrar
        </ArenaButton>
      }
    >
      {error ? (
        <p>No encontramos la consulta de esta cifra.</p>
      ) : datos ? (
        <BloqueConsulta consulta={datos} />
      ) : (
        <ArenaSkeleton variant="text" lines={4} />
      )}
    </ArenaDialog>
  );
}
