import type { Query } from '../api/types';
import { formatInUnit, formatShortDate } from '../format';
import { sourceTitle } from './SeriesChart';

function cell(value: unknown, unit: Query['units'][string] | undefined): string {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'number') {
    return formatInUnit(value, unit ?? 'units');
  }
  if (typeof value === 'boolean') {
    return value ? 'Sí' : 'No';
  }
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return formatShortDate(value);
  }
  return String(value);
}

function heading(column: string): string {
  const words = column.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const HIDDEN_COLUMNS = new Set(['id', 'alerta_id']);

export function QueryBlock({ query }: { query: Query }) {
  const rows = query.rows ?? [];
  const columns = rows.length > 0 ? Object.keys(rows[0]).filter((c) => !HIDDEN_COLUMNS.has(c)) : [];
  return (
    <div className="arena-stack arena-stack--group query">
      <p className="query__description">{query.description}</p>
      {rows.length > 0 ? (
        <div className="query__table-wrap">
          <table className="query__table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column} scope="col">
                    {heading(column)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  {columns.map((column) => (
                    <td key={column}>{cell(row[column], query.units?.[column])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <p className="text-muted query__source">
        {query.source === 'alertas' ? 'Fuente: registro de alertas de Centinela' : `Fuente: ${sourceTitle(query.source)}`}
      </p>
      <details className="collapsible">
        <summary>Ver la consulta técnica</summary>
        <pre className="query__sql">
          <code>{query.sql}</code>
        </pre>
      </details>
    </div>
  );
}
