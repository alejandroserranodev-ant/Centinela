import type { Consulta, FuenteConsulta } from '../api/types';

function nombreFuente(fuente: FuenteConsulta): string {
  return fuente === 'alertas' ? 'registro de alertas de Centinela' : `vista ${fuente}`;
}

export function BloqueConsulta({ consulta }: { consulta: Consulta }) {
  return (
    <div className="arena-stack arena-stack--group consulta">
      <p className="consulta__descripcion">{consulta.descripcion}</p>
      <p className="texto-tenue">
        Fuente: <code>{nombreFuente(consulta.vista)}</code> · consulta <code>{consulta.id}</code>
      </p>
      <pre className="consulta__sql">
        <code>{consulta.sql}</code>
      </pre>
    </div>
  );
}
