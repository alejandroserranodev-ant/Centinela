import type { Query, QuerySource } from '../api/types';

function sourceName(source: QuerySource): string {
  return source === 'alertas' ? 'registro de alertas de Centinela' : `vista ${source}`;
}

export function QueryBlock({ query }: { query: Query }) {
  return (
    <div className="arena-stack arena-stack--group query">
      <p className="query__description">{query.description}</p>
      <p className="text-muted">
        Fuente: <code>{sourceName(query.source)}</code> · consulta <code>{query.id}</code>
      </p>
      <pre className="query__sql">
        <code>{query.sql}</code>
      </pre>
    </div>
  );
}
