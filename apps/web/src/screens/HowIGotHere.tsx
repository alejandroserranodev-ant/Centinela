import { useEffect, useState } from 'react';
import { ArenaSection, ArenaSkeleton } from '@dravensoft/arena-react';
import { getQuery } from '../api/client';
import type { Alert, Query } from '../api/types';
import { QueryBlock } from '../common/QueryBlock';

export function alertQueryIds(alert: Alert): string[] {
  const ids = [
    ...alert.title.figures.map((f) => f.queryId),
    alert.pesosAtRisk.queryId,
    ...(alert.recoverablePerMonth ? [alert.recoverablePerMonth.queryId] : []),
    ...(alert.cause.kind === 'identified'
      ? [
          ...alert.cause.sentence.figures.map((f) => f.queryId),
          ...alert.cause.evidence.flatMap((e) => [e.queryId, ...e.claim.figures.map((f) => f.queryId)]),
        ]
      : alert.cause.queriesReviewed),
    ...alert.actions.flatMap((a) => [...a.description.figures.map((f) => f.queryId), ...(a.impact ? [a.impact.figure.queryId] : [])]),
  ];
  return [...new Set(ids)];
}

export function HowIGotHere({ alert }: { alert: Alert }) {
  const [queries, setQueries] = useState<Query[] | null>(null);

  useEffect(() => {
    setQueries(null);
    Promise.all(alertQueryIds(alert).map((id) => getQuery(id))).then(setQueries, () => setQueries([]));
  }, [alert]);

  return (
    <ArenaSection
      title="Cómo llegué aquí"
      headingLevel="h3"
      description="Cada cifra de esta alerta sale de una de estas consultas a los datos de la operación."
    >
      <details className="collapsible">
        <summary>{queries ? `Ver las ${queries.length} consultas` : 'Ver las consultas'}</summary>
        {queries ? (
          <ol className="arena-stack query-list">
            {queries.map((q) => (
              <li key={q.id}>
                <QueryBlock query={q} />
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
