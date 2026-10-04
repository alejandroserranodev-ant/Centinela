import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArenaButton,
  ArenaErrorState,
  ArenaSkeleton,
  ArenaTable,
  ArenaTableCell,
  ArenaTableRow,
  ArenaTag,
  type ArenaTableColumn,
} from '@dravensoft/arena-react';
import { ApiError, listExpansions, retireExpansion } from '../api/client';
import type { TreeExpansion } from '../api/types';
import { agentName } from '../actor';
import { inactiveLine } from '../expansion';
import { fillSentence, formatShortDate } from '../format';
import { useSimulation } from '../state/Simulation';
import { ReasonDialog } from './ReasonDialog';

const COLUMNS: ArenaTableColumn[] = [
  { header: 'Día de la operación', mono: true, width: 'calc(var(--sp-1) * 28)' },
  { header: 'Quién' },
  { header: 'Cambio' },
  { header: 'Alertas que lo sostienen' },
  { header: 'Estado' },
];

export function Expansions({ allowed }: { allowed: boolean }) {
  const { notify } = useSimulation();
  const navigate = useNavigate();
  const [expansions, setExpansions] = useState<TreeExpansion[] | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [retiring, setRetiring] = useState<TreeExpansion | null>(null);

  useEffect(() => {
    setFailure(null);
    listExpansions().then(setExpansions, (e: unknown) => {
      if (!(e instanceof ApiError && e.status === 401)) {
        setFailure(e instanceof Error ? e.message : 'No se pudieron cargar los cambios del árbol.');
      }
    });
  }, [attempt]);

  if (failure !== null) {
    return (
      <ArenaErrorState
        headingLevel="h2"
        title="No pudimos cargar los cambios del árbol"
        message={failure}
        retryLabel="Reintentar"
        onRetry={() => setAttempt((n) => n + 1)}
      />
    );
  }
  if (expansions === null) {
    return <ArenaSkeleton variant="text" lines={4} />;
  }

  const retire = async (reason: string) => {
    if (retiring === null) {
      return;
    }
    let retired: TreeExpansion;
    try {
      retired = await retireExpansion(retiring.id, reason);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setExpansions(await listExpansions().catch(() => expansions));
      }
      throw e;
    }
    const patched = expansions.map((e) => (e.id === retired.id ? retired : e));
    setExpansions(await listExpansions().catch(() => patched));
    setRetiring(null);
    notify({ tone: 'success', title: 'Cambio retirado', message: 'Aplica desde el próximo día.' });
  };

  return (
    <div className="arena-stack arena-stack--group">
      <p className="text-muted">
        Los cambios que los agentes hicieron a su parte del árbol de decisión, el más reciente primero. Cada uno aplica desde el
        día siguiente y puede retirarse; retirarlo no espera a «Guardar cambios».
      </p>
      <ArenaTable label="Cambios del árbol de decisión" columns={COLUMNS} empty="Los agentes aún no han cambiado el árbol.">
        {expansions.map((e) => (
          <ArenaTableRow key={e.id}>
            <ArenaTableCell>{e.simulatedDate ? formatShortDate(e.simulatedDate) : 'Sin día'}</ArenaTableCell>
            <ArenaTableCell>{agentName(e.agent)}</ArenaTableCell>
            <ArenaTableCell>{e.description}</ArenaTableCell>
            <ArenaTableCell>
              <span className="arena-stack">
                {e.evidence.map((evidence) => (
                  <button key={evidence.alertId} type="button" className="link" onClick={() => navigate(`/alertas/${evidence.alertId}`)}>
                    {fillSentence(evidence.title.text, evidence.title.figures)}
                  </button>
                ))}
              </span>
            </ArenaTableCell>
            <ArenaTableCell>
              {e.status === 'retired' ? (
                <span className="text-muted">
                  Retirado por {e.retiredBy ?? 'alguien'}: {e.retireReason}
                </span>
              ) : e.status === 'inactive' ? (
                <span className="arena-stack">
                  <ArenaTag>Inactivo</ArenaTag>
                  <span className="text-muted">{inactiveLine(e.inactiveReason)}</span>
                </span>
              ) : (
                <span className="arena-stack">
                  <ArenaTag>Activo</ArenaTag>
                  {allowed ? (
                    <ArenaButton variant="ghost" icon="ph-bold ph-arrow-counter-clockwise" onClick={() => setRetiring(e)}>
                      Retirar
                    </ArenaButton>
                  ) : null}
                </span>
              )}
            </ArenaTableCell>
          </ArenaTableRow>
        ))}
      </ArenaTable>
      <ReasonDialog
        open={retiring !== null}
        eyebrow="Árbol de decisión"
        title="Retirar este cambio"
        hint="El árbol vuelve a decidir como antes de este cambio desde el próximo día. Las alertas que lo sostuvieron no vuelven a contar."
        label="Por qué lo retiras"
        missing="Escribe por qué lo retiras"
        failure="No se pudo retirar el cambio. Inténtalo de nuevo."
        confirm="Retirar"
        variant="danger"
        icon="ph-bold ph-arrow-counter-clockwise"
        onClose={() => setRetiring(null)}
        onSend={retire}
      />
    </div>
  );
}
