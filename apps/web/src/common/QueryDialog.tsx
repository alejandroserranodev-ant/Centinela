import { useEffect, useState } from 'react';
import { ArenaButton, ArenaDialog, ArenaSkeleton } from '@dravensoft/arena-react';
import { getQuery } from '../api/client';
import type { Query } from '../api/types';
import { useSimulation } from '../state/Simulation';
import { QueryBlock } from './QueryBlock';

export function QueryDialog() {
  const { openQueryId, closeQuery } = useSimulation();
  const [query, setQuery] = useState<Query | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setQuery(null);
    setError(false);
    if (openQueryId) {
      getQuery(openQueryId).then(setQuery, () => setError(true));
    }
  }, [openQueryId]);

  return (
    <ArenaDialog
      open={openQueryId !== null}
      eyebrow="Cómo llegué aquí"
      title="De dónde sale esta cifra"
      width="calc(var(--sp-1) * 160)"
      fillBelow="sm"
      onClose={closeQuery}
      footer={
        <ArenaButton variant="secondary" onClick={closeQuery}>
          Cerrar
        </ArenaButton>
      }
    >
      {error ? (
        <p>No encontramos la consulta de esta cifra.</p>
      ) : query ? (
        <QueryBlock query={query} />
      ) : (
        <ArenaSkeleton variant="text" lines={4} />
      )}
    </ArenaDialog>
  );
}
