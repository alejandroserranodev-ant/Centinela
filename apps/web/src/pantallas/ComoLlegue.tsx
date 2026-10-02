import { useEffect, useState } from 'react';
import { ArenaSection, ArenaSkeleton } from '@dravensoft/arena-react';
import { consulta } from '../api/client';
import type { Alerta, Consulta } from '../api/types';
import { BloqueConsulta } from '../comun/BloqueConsulta';

export function consultasDeAlerta(alerta: Alerta): string[] {
  const ids = [
    ...alerta.titulo.cifras.map((c) => c.consultaId),
    alerta.pesosEnRiesgo.consultaId,
    ...(alerta.recuperableMes ? [alerta.recuperableMes.consultaId] : []),
    ...(alerta.causa.tipo === 'identificada'
      ? [
          ...alerta.causa.frase.cifras.map((c) => c.consultaId),
          ...alerta.causa.evidencia.flatMap((e) => [e.consultaId, ...e.afirmacion.cifras.map((c) => c.consultaId)]),
        ]
      : alerta.causa.consultasRevisadas),
    ...alerta.acciones.flatMap((a) => [
      ...a.descripcion.cifras.map((c) => c.consultaId),
      ...(a.impacto ? [a.impacto.cifra.consultaId] : []),
    ]),
  ];
  return [...new Set(ids)];
}

export function ComoLlegue({ alerta }: { alerta: Alerta }) {
  const [consultas, setConsultas] = useState<Consulta[] | null>(null);

  useEffect(() => {
    setConsultas(null);
    Promise.all(consultasDeAlerta(alerta).map((id) => consulta(id))).then(setConsultas, () => setConsultas([]));
  }, [alerta]);

  return (
    <ArenaSection
      title="Cómo llegué aquí"
      headingLevel="h3"
      description="Cada cifra de esta alerta sale de una de estas consultas a los datos de la operación."
    >
      <details className="plegable">
        <summary>{consultas ? `Ver las ${consultas.length} consultas` : 'Ver las consultas'}</summary>
        {consultas ? (
          <ol className="arena-stack consultas">
            {consultas.map((c) => (
              <li key={c.id}>
                <BloqueConsulta consulta={c} />
              </li>
            ))}
          </ol>
        ) : (
          <ArenaSkeleton variant="text" lines={4} />
        )}
      </details>
    </ArenaSection>
  );
}
