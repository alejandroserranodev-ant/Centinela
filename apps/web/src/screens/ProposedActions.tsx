import { useEffect, useState } from 'react';
import { ArenaButton, ArenaCard, ArenaKeyValue, ArenaRadio, ArenaRadioGroup } from '@dravensoft/arena-react';
import { ApiError, decide, getSettings } from '../api/client';
import type { Action, ActionType, Alert, AutonomyLevel, Decision } from '../api/types';
import { Confidence } from '../common/Badges';
import { LinkedFigure, SentenceWithFigures } from '../common/SentenceWithFigures';
import { useSimulation } from '../state/Simulation';
import { formatFigure } from '../format';
import { parameterName } from '../actionParameters';
import { EditDialog } from './EditDialog';
import { ReasonDialog } from './ReasonDialog';

export const TYPE: Record<ActionType, string> = {
  email_draft: 'Borrador de correo',
  task: 'Tarea',
  purchase_order_draft: 'Borrador de orden de compra',
  price_change_draft: 'Borrador de ajuste de precio',
};

const LEVEL: Record<Action['confidence']['level'], string> = { high: 'alta', medium: 'media', low: 'baja' };

function actionSummary(action: Action): string {
  const impact = action.impact
    ? `${formatFigure(action.impact.figure)} ${action.impact.period === 'month' ? 'al mes' : 'una vez'}`
    : 'Sin impacto en pesos estimado';
  return `${TYPE[action.type]} · ${impact} · confianza ${LEVEL[action.confidence.level]}`;
}

export function ProposedActions({ alert }: { alert: Alert }) {
  const { notify, changed } = useSimulation();
  const [chosenId, setChosenId] = useState(alert.actions[0].id);
  const [approving, setApproving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [autonomy, setAutonomy] = useState<Partial<Record<ActionType, AutonomyLevel>>>({});
  const chosen = alert.actions.find((a) => a.id === chosenId) ?? alert.actions[0];
  const informOnly = autonomy[chosen.type] === 'inform';

  useEffect(() => {
    getSettings().then(
      (settings) => setAutonomy(settings.autonomy),
      () => setAutonomy({}),
    );
  }, []);

  const send = async (decision: Decision) => {
    try {
      const result = await decide(alert.id, decision);
      if (decision.kind === 'reject') {
        notify({ tone: 'neutral', title: 'Propuesta rechazada', message: 'El motivo quedó en la bitácora.' });
      } else if (decision.kind === 'request_changes') {
        notify({ tone: 'neutral', title: 'Cambios solicitados', message: 'La propuesta se revisará con tu motivo.' });
      } else {
        notify(
          result.executedAction
            ? { tone: 'success', title: `Aprobada: ${chosen.title}`, message: result.executedAction.result }
            : { tone: 'neutral', title: `Aprobada, sin ejecutar: ${chosen.title}`, message: 'La alerta dice por qué.' },
        );
      }
      setEditing(false);
      setRejecting(false);
      setRequesting(false);
      changed();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        notify({ tone: 'danger', title: 'No se registró la decisión', message: `${e.message}. Recargamos su estado actual.` });
        setEditing(false);
        setRejecting(false);
        setRequesting(false);
        changed();
        return;
      }
      throw e;
    }
  };

  const approve = async () => {
    setApproving(true);
    try {
      await send({ kind: 'approve', actionId: chosen.id });
    } catch (e) {
      notify({
        tone: 'danger',
        title: 'No se pudo aprobar',
        message: e instanceof ApiError && (e.status === 403 || e.status === 422) ? e.message : 'Inténtalo de nuevo en unos segundos.',
      });
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="arena-stack">
      {alert.actions.length > 1 ? (
        <ArenaRadioGroup ariaLabel="Acción a aprobar" value={chosen.id} onChange={setChosenId}>
          {alert.actions.map((action) => (
            <ArenaRadio key={action.id} value={action.id} label={action.title} hint={actionSummary(action)} />
          ))}
        </ArenaRadioGroup>
      ) : null}
      <ArenaCard eyebrow={TYPE[chosen.type]} title={chosen.title} headingLevel="h4" action={<Confidence level={chosen.confidence.level} />}>
        <div className="arena-stack arena-stack--group">
          <p>
            <SentenceWithFigures text={chosen.description.text} figures={chosen.description.figures} />
          </p>
          <p>
            <span className="eyebrow">Impacto estimado</span>{' '}
            {chosen.impact ? (
              <>
                <LinkedFigure figure={chosen.impact.figure} /> {chosen.impact.period === 'month' ? 'al mes' : 'una sola vez'}
              </>
            ) : (
              'sin impacto en pesos estimado'
            )}
          </p>
          {chosen.confidence.assumptions.length > 0 ? (
            <div>
              <span className="eyebrow">Supone que</span>
              <ul className="assumptions">
                {chosen.confidence.assumptions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <ArenaKeyValue
            rows={Object.entries(chosen.parameters).map(([key, value]) => ({
              term: parameterName(key),
              value: String(value),
              numeric: typeof value === 'number',
            }))}
          />
        </div>
      </ArenaCard>
      {alert.canDecide ? (
        <>
          <div className="arena-row arena-row--component decision">
            {informOnly ? null : (
              <>
                <ArenaButton variant="primary" icon="ph-bold ph-check" loading={approving} onClick={approve}>
                  Aprobar
                </ArenaButton>
                <ArenaButton variant="secondary" icon="ph-bold ph-pencil-simple" onClick={() => setEditing(true)}>
                  Editar
                </ArenaButton>
              </>
            )}
            {alert.changesRequested ? null : (
              <ArenaButton variant="secondary" icon="ph-bold ph-arrow-counter-clockwise" onClick={() => setRequesting(true)}>
                Solicitar cambios
              </ArenaButton>
            )}
            <ArenaButton variant="danger" icon="ph-bold ph-x" onClick={() => setRejecting(true)}>
              Rechazar
            </ArenaButton>
          </div>
          {informOnly ? <p className="text-muted">Este tipo de acción solo informa: no se aprueba desde Centinela.</p> : null}
          <p className="text-muted">
            Aprobar deja un borrador o una tarea: nada se envía ni se publica hasta que una persona lo haga.
          </p>
          {alert.changesRequested ? (
            <p className="text-muted">Ya se pidieron cambios una vez: queda aprobar, editar o rechazar.</p>
          ) : null}
        </>
      ) : (
        <p className="text-muted">Decide: {alert.decidedBy ?? 'Gerencia'}</p>
      )}
      <EditDialog
        action={chosen}
        open={editing}
        onClose={() => setEditing(false)}
        onApprove={(parameters) => send({ kind: 'edit', actionId: chosen.id, parameters })}
      />
      <ReasonDialog
        open={requesting}
        eyebrow="Solicitar cambios"
        title="¿Qué debe cambiar en la propuesta?"
        hint="El motivo queda en la bitácora, y la propuesta se revisa una sola vez."
        label="Qué debe cambiar"
        missing="Escribe qué debe cambiar para continuar."
        failure="No se pudo registrar la solicitud. Inténtalo de nuevo."
        confirm="Solicitar cambios"
        variant="primary"
        icon="ph-bold ph-arrow-counter-clockwise"
        onClose={() => setRequesting(false)}
        onSend={(reason) => send({ kind: 'request_changes', reason })}
      />
      <ReasonDialog
        open={rejecting}
        eyebrow="Rechazar"
        title="¿Por qué rechazas la propuesta?"
        hint="El motivo queda en la bitácora junto a tu nombre."
        label="Motivo del rechazo"
        missing="Escribe el motivo del rechazo para continuar."
        failure="No se pudo registrar el rechazo. Inténtalo de nuevo."
        confirm="Rechazar"
        variant="danger"
        icon="ph-bold ph-x"
        onClose={() => setRejecting(false)}
        onSend={(reason) => send({ kind: 'reject', reason })}
      />
    </div>
  );
}
