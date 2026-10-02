import type { Query } from '../api/types';
import { sourceTitle } from './SeriesChart';

export function QueryBlock({ query }: { query: Query }) {
  return (
    <div className="arena-stack arena-stack--group query">
      <p className="query__description">{query.description}</p>
      <p className="text-muted">
        {query.source === 'alertas' ? (
          'Fuente: registro de alertas de Centinela'
        ) : (
          <>
            Fuente: {sourceTitle(query.source)} (<code>{query.source}</code>)
          </>
        )}
      </p>
      <pre className="query__sql">
        <code>{query.sql}</code>
      </pre>
    </div>
  );
}
