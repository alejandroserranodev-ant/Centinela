import type { ReactNode } from 'react';
import type { Figure } from '../api/types';
import { useSimulation } from '../state/Simulation';
import { formatFigure, formatFigureInText } from '../format';

interface Span {
  start: number;
  end: number;
  figure: Figure;
}

function locate(text: string, figures: Figure[]): Span[] {
  const spans: Span[] = [];
  for (const figure of figures) {
    const sought = formatFigureInText(figure);
    let from = 0;
    while (from <= text.length) {
      const start = text.indexOf(sought, from);
      if (start < 0) {
        break;
      }
      const end = start + sought.length;
      if (!spans.some((s) => start < s.end && end > s.start)) {
        spans.push({ start, end, figure });
        break;
      }
      from = start + 1;
    }
  }
  return spans.sort((a, b) => a.start - b.start);
}

function filled(text: string, figures: Figure[]): string {
  return text.replace(/\{(\d+)\}/g, (placeholder, index: string) => {
    const figure = figures[Number(index)];
    return figure ? formatFigureInText(figure) : placeholder;
  });
}

export function SentenceWithFigures({ text: written, figures }: { text: string; figures: Figure[] }) {
  const { openQuery } = useSimulation();
  const text = filled(written, figures);
  const parts: ReactNode[] = [];
  let cursor = 0;
  for (const span of locate(text, figures)) {
    parts.push(text.slice(cursor, span.start));
    parts.push(
      <button
        key={span.start}
        type="button"
        className="figure-link"
        title="Ver de dónde sale esta cifra"
        onClick={() => openQuery(span.figure.queryId)}
      >
        {text.slice(span.start, span.end)}
        <span className="arena-sr-only">, ver de dónde sale</span>
      </button>,
    );
    cursor = span.end;
  }
  parts.push(text.slice(cursor));
  return <>{parts}</>;
}

export function LinkedFigure({ figure }: { figure: Figure }) {
  const { openQuery } = useSimulation();
  return (
    <button type="button" className="figure-link" title="Ver de dónde sale esta cifra" onClick={() => openQuery(figure.queryId)}>
      {formatFigure(figure)}
      <span className="arena-sr-only">, ver de dónde sale</span>
    </button>
  );
}
