import type { ReactNode } from 'react';
import { ArenaAlert, ArenaButton, ArenaDialog, ArenaTab, ArenaTabs, ArenaTag } from '@dravensoft/arena-react';
import type { Alert } from '../api/types';
import { Confidence, Labels } from '../common/Badges';
import { LinkedFigure, SentenceWithFigures } from '../common/SentenceWithFigures';
import { explainedByRemaining } from '../alert';
import { formatDate } from '../format';
import { TYPE } from './ProposedActions';

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="arena-stack arena-stack--group">
      <span className="eyebrow">{label}</span>
      {children}
    </div>
  );
}

function Detection({ alert }: { alert: Alert }) {
  return (
    <div className="arena-stack">
      <Field label="Qué detectó">
        <p>
          <SentenceWithFigures text={alert.title.text} figures={alert.title.figures} />
        </p>
      </Field>
      {alert.labels.length > 0 ? (
        <Field label="Sobre">
          <div className="arena-row">
            <Labels labels={alert.labels} />
          </div>
        </Field>
      ) : null}
      <Field label="Detectada el">
        <p>{formatDate(alert.simulatedDate)}</p>
      </Field>
      <Field label="En riesgo">
        <p>
          <LinkedFigure figure={alert.pesosAtRisk} />
        </p>
      </Field>
    </div>
  );
}

function Analysis({ alert }: { alert: Alert }) {
  if (alert.cause.kind !== 'identified') {
    if (explainedByRemaining(alert.cause, alert.status === 'merged')) {
      return <p>La causa está en la alerta que queda, que la explica con su evidencia.</p>;
    }
    return (
      <ArenaAlert tone="warning" icon="ph-bold ph-question" title="No encontramos evidencia suficiente para explicar la causa">
        {alert.cause.reason}
      </ArenaAlert>
    );
  }
  return (
    <div className="arena-stack">
      <Field label="Causa">
        <p className="detail__cause">
          <SentenceWithFigures text={alert.cause.sentence.text} figures={alert.cause.sentence.figures} />
        </p>
      </Field>
      {alert.cause.evidence.length > 0 ? (
        <Field label="Evidencia">
          <ul className="arena-stack arena-stack--group evidence-list">
            {alert.cause.evidence.map((e) => (
              <li key={e.queryId + e.claim.text}>
                <SentenceWithFigures text={e.claim.text} figures={e.claim.figures} />
              </li>
            ))}
          </ul>
        </Field>
      ) : null}
      {alert.confidence.assumptions.length > 0 ? (
        <Field label="Supone que">
          <ul className="assumptions">
            {alert.confidence.assumptions.map((assumption) => (
              <li key={assumption}>{assumption}</li>
            ))}
          </ul>
        </Field>
      ) : null}
      <div className="arena-row">
        <Confidence level={alert.confidence.level} />
      </div>
    </div>
  );
}

function Strategy({ alert }: { alert: Alert }) {
  if (alert.actions.length === 0 && alert.status === 'merged') {
    return <p>Esta alerta se unió a otra con la misma causa, y sus acciones se proponen allí.</p>;
  }
  if (alert.actions.length === 0) {
    return (
      <ArenaAlert tone="info" title="Sin acciones propuestas">
        Ninguna acción encaja con esta causa, así que la alerta queda para revisión manual.
      </ArenaAlert>
    );
  }
  return (
    <div className="arena-stack">
      <Field label={alert.actions.length === 1 ? 'Acción propuesta' : `${alert.actions.length} acciones propuestas`}>
        <ol className="arena-stack evidence-list">
          {alert.actions.map((action) => (
            <li key={action.id} className="arena-stack arena-stack--group">
              <div className="arena-row">
                <strong>{action.title}</strong>
                <ArenaTag>{TYPE[action.type]}</ArenaTag>
              </div>
              <p>
                <SentenceWithFigures text={action.description.text} figures={action.description.figures} />
              </p>
              <p className="text-muted">
                {action.impact ? (
                  <>
                    Impacto estimado: <LinkedFigure figure={action.impact.figure} />{' '}
                    {action.impact.period === 'month' ? 'al mes' : 'una sola vez'}
                  </>
                ) : (
                  'Sin impacto en pesos estimado'
                )}
              </p>
            </li>
          ))}
        </ol>
      </Field>
      {alert.recoverablePerMonth ? (
        <Field label="Recuperable">
          <p>
            <LinkedFigure figure={alert.recoverablePerMonth} /> al mes
          </p>
        </Field>
      ) : null}
    </div>
  );
}

function Execution({ alert }: { alert: Alert }) {
  if (alert.executedAction) {
    const executed = alert.executedAction;
    const action = alert.actions.find((a) => a.id === executed.actionId);
    return (
      <div className="arena-stack">
        <Field label="Acción ejecutada">
          <p>{action ? action.title : executed.actionId}</p>
        </Field>
        <Field label="Resultado">
          <p>{executed.result}</p>
        </Field>
      </div>
    );
  }
  if (alert.status === 'rejected') {
    return (
      <ArenaAlert tone="info" title="Sin ejecución">
        La propuesta fue rechazada, así que no se ejecutó ninguna acción.
      </ArenaAlert>
    );
  }
  if (alert.status === 'merged') {
    return (
      <ArenaAlert tone="info" title="Sin ejecución">
        Esta alerta se unió a otra con la misma causa, y la acción se decide allí.
      </ArenaAlert>
    );
  }
  if (alert.status === 'approved') {
    return (
      <ArenaAlert tone="info" title="Aprobada, sin resultado todavía">
        La alerta muestra por qué la acción no se ha ejecutado.
      </ArenaAlert>
    );
  }
  return (
    <ArenaAlert tone="info" icon="ph-bold ph-clock" title="Pendiente de aprobación">
      Ninguna acción se ejecuta hasta que una persona apruebe una de las propuestas.
    </ArenaAlert>
  );
}

export function AgentPhasesModal({ alert, open, onClose }: { alert: Alert; open: boolean; onClose: () => void }) {
  return (
    <ArenaDialog
      open={open}
      eyebrow="Cómo trabajaron los agentes"
      title="Fases del análisis"
      width="calc(var(--sp-1) * 180)"
      fillBelow="sm"
      onClose={onClose}
      footer={
        <ArenaButton variant="secondary" onClick={onClose}>
          Cerrar
        </ArenaButton>
      }
    >
      <div className="arena-stack">
        <p className="text-muted">Vigía detecta, Analista explica la causa, Estratega propone y Ejecutor actúa solo después de que una persona aprueba.</p>
        <ArenaTabs defaultValue="vigia">
          <ArenaTab value="vigia" label="Vigía">
            <Detection alert={alert} />
          </ArenaTab>
          <ArenaTab value="analista" label="Analista">
            <Analysis alert={alert} />
          </ArenaTab>
          <ArenaTab value="estratega" label="Estratega">
            <Strategy alert={alert} />
          </ArenaTab>
          <ArenaTab value="ejecutor" label="Ejecutor">
            <Execution alert={alert} />
          </ArenaTab>
        </ArenaTabs>
      </div>
    </ArenaDialog>
  );
}
