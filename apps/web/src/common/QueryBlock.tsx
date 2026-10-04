import { useState } from 'react';
import type { Query } from '../api/types';
import { sourceTitle } from './SeriesChart';

const pesosFmt = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
const numFmt = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 });
const dateFmt = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeZone: 'America/Bogota' });

function formatCell(key: string, value: unknown): string {
  if (value === null || value === undefined) return '—';
  const k = key.toLowerCase();

  // Dates
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    try { return dateFmt.format(new Date(value.length === 10 ? `${value}T12:00:00-05:00` : value)); }
    catch { return value; }
  }

  // Percentages
  if (typeof value === 'number' && (k.endsWith('_pct') || k.includes('porcentaje') || k.includes('brecha') || k.includes('variacion') || k.includes('incremento'))) {
    return `${numFmt.format(value)} %`;
  }

  // Peso amounts — large numbers in peso-named columns
  if (typeof value === 'number' && Math.abs(value) >= 1000 && (
    k.includes('saldo') || k.includes('valor') || k.includes('pesos') ||
    k.includes('costo') || k.includes('precio') || k.includes('monto') ||
    k.includes('total') || k.includes('cupo') || k.includes('recuper') ||
    k.includes('perdida') || k.includes('ventas') || k.includes('margen') ||
    k.includes('lista')
  )) {
    return pesosFmt.format(value);
  }

  if (typeof value === 'number') return numFmt.format(value);
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  return String(value);
}

function headerLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\bpct\b/gi, '%')
    .replace(/\bprom\b/gi, 'prom.')
    .replace(/\bid\b/gi, 'ID')
    .replace(/^(.)/, (c) => c.toUpperCase());
}

export function QueryBlock({ query }: { query: Query }) {
  const [showSql, setShowSql] = useState(false);
  const rows = query.rows ?? [];
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <div className="arena-stack arena-stack--group query">

      {/* 1. Descripción en lenguaje de negocio */}
      <p className="query__description">{query.description}</p>

      {/* 2. Tabla de datos reales */}
      {rows.length > 0 && (
        <div className="query__table-wrap">
          <table className="query__table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col}>{headerLabel(col)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {columns.map((col) => (
                    <td key={col}>{formatCell(col, row[col])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 3. Fuente */}
      <p className="text-muted query__source">
        {query.source === 'alertas' ? (
          'Fuente: registro de alertas de Centinela'
        ) : (
          <>Fuente: {sourceTitle(query.source)} (<code>{query.source}</code>)</>
        )}
      </p>

      {/* 4. SQL colapsado — solo para usuarios técnicos */}
      <button
        type="button"
        className="link"
        onClick={() => setShowSql((v) => !v)}
      >
        {showSql ? '▲ Ocultar consulta técnica' : '▼ Ver consulta técnica'}
      </button>
      {showSql && (
        <pre className="query__sql">
          <code>{query.sql}</code>
        </pre>
      )}
    </div>
  );
}
