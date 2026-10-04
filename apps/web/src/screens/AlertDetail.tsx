import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArenaAlert,
  ArenaButton,
  ArenaErrorState,
  ArenaSection,
  ArenaSkeleton,
  ArenaSpinner,
  useArenaViewportBelow,
} from '@dravensoft/arena-react';
import { getAlert, getQuery } from '../api/client';
import type { Alert, Evidence, MergedAlert, Query } from '../api/types';
import { Confidence, Labels, Severity, Status } from '../common/Badges';
import { LinkedFigure, SentenceWithFigures } from '../common/SentenceWithFigures';
import { SeriesChart, sourceTitle } from '../common/SeriesChart';
import { useSimulation } from '../state/Simulation';
import { formatDate } from '../format';
import { HowIGotHere } from './HowIGotHere';
import { ProposedActions } from './ProposedActions';

function Proof({ evidence }: { evidence: Evidence }) {
  const [source, setSource] = useState<Query | null>(null);
  useEffect(() => {
    getQuery(evidence.queryId).then(setSource, () => setSource(null));
  }, [evidence.queryId]);
  const unit = evidence.claim.figures[0]?.unit ?? 'units';
  return (
    <li className="arena-stack arena-stack--group">
      <p>
        <SentenceWithFigures text={evidence.claim.text} figures={evidence.claim.figures} />
      </p>
      {evidence.series && source ? (
        <SeriesChart title={sourceTitle(source.source)} name={source.description} series={evidence.series} unit={unit} />
      ) : null}
    </li>
  );
}

function Merged({ alert }: { alert: MergedAlert }) {
  return (
    <li className="arena-stack arena-stack--group">
      <p>
        <SentenceWithFigures text={alert.title.text} figures={alert.title.figures} />
      </p>
      <p className="text-muted">
        Detectada el {formatDate(alert.simulatedDate)}, con <LinkedFigure figure={alert.pesosAtRisk} /> en riesgo que no se
        suman a los de esta alerta.
      </p>
      {alert.cause.kind === 'identified' ? (
        <ul className="arena-stack evidence-list">
          {alert.cause.evidence.map((e) => (
            <Proof key={e.queryId + e.claim.text} evidence={e} />
          ))}
        </ul>
      ) : (
        <p>{alert.cause.reason}</p>
      )}
    </li>
  );
}

function Outcome({ alert }: { alert: Alert }) {
  if (alert.status === 'rejected') {
    return (
      <ArenaAlert tone="info" title="Rechazaste esta propuesta">
        El motivo está en la bitácora. La alerta no vuelve a la bandeja de pendientes.
      </ArenaAlert>
    );
  }
  if (alert.status === 'approved' || alert.status === 'executed') {
    const action = alert.actions.find((a) => a.id === alert.executedAction?.actionId);
    return (
      <ArenaAlert tone="success" title={action ? `Aprobada: ${action.title}` : 'Aprobada'}>
        {alert.executedAction?.result ?? 'La acción está en curso.'}
      </ArenaAlert>
    );
  }
  return null;
}

export function AlertDetail({ id }: { id: string }) {
  const navigate = useNavigate();
  const mobile = useArenaViewportBelow('lg');
  const { version, openChat } = useSimulation();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
    getAlert(id).then(setAlert, () => setFailed(true));
  }, [id, version]);

  useEffect(() => {
    setAlert(null);
  }, [id]);

  const back = mobile ? (
    <div>
      <ArenaButton variant="ghost" size="sm" icon="ph-bold ph-arrow-left" onClick={() => navigate('/')}>
        Volver a la bandeja
      </ArenaButton>
    </div>
  ) : null;

  if (failed) {
    return (
      <div className="arena-stack">
        {back}
        <ArenaErrorState
          icon="ph-bold ph-magnifying-glass"
          title="No encontramos esta alerta"
          message="Puede que el enlace sea de otro día simulado. Vuelve a la bandeja para ver las alertas vigentes."
          retryLabel="Volver a la bandeja"
          onRetry={() => navigate('/')}
        />
      </div>
    );
  }

  if (!alert || alert.id !== id) {
    return <ArenaSkeleton variant="text" lines={8} />;
  }

  const pending = alert.status === 'proposed';
  const analyzing = alert.status === 'new' || alert.status === 'analyzing';

  return (
    <article className="arena-stack arena-stack--section detail" aria-labelledby="alert-title">
      {back}
      <header className="arena-stack arena-stack--group">
        <div className="arena-row detail__badges">
          <Severity level={alert.severity} />
          <Labels labels={alert.labels} />
          <Status status={alert.status} />
          <Confidence level={alert.confidence.level} />
          <time className="text-muted" dateTime={alert.simulatedDate}>
            Detectada el {formatDate(alert.simulatedDate)}
          </time>
        </div>
        <h2 id="alert-title" className="detail__title">
          <SentenceWithFigures text={alert.title.text} figures={alert.title.figures} />
        </h2>
        <p className="detail__money">
          <span>
            <span className="eyebrow">En riesgo</span> <LinkedFigure figure={alert.pesosAtRisk} />
          </span>
          {alert.recoverablePerMonth ? (
            <span>
              <span className="eyebrow">Recuperable</span> <LinkedFigure figure={alert.recoverablePerMonth} /> al mes
            </span>
          ) : null}
        </p>
        <div>
          <ArenaButton variant="ghost" size="sm" icon="ph-bold ph-chat-circle-text" onClick={() => openChat(alert.id)}>
            Preguntar sobre esta alerta
          </ArenaButton>
        </div>
      </header>

      <Outcome alert={alert} />

      {analyzing ? (
        <div className="arena-row analyzing">
          <ArenaSpinner size="sm" label="Analizando la alerta" />
          <p>Estamos buscando la causa y preparando la propuesta. Aparece aquí en unos segundos.</p>
        </div>
      ) : (
        <>
          <ArenaSection title="Por qué" headingLevel="h3">
            {alert.cause.kind === 'identified' ? (
              <div className="arena-stack arena-stack--group">
                <p className="detail__cause">
                  <SentenceWithFigures text={alert.cause.sentence.text} figures={alert.cause.sentence.figures} />
                </p>
                {alert.confidence.assumptions.length > 0 ? (
                  <p className="text-muted">
                    Supone que {alert.confidence.assumptions.map((a) => a.charAt(0).toLowerCase() + a.slice(1)).join('; ')}.
                  </p>
                ) : null}
              </div>
            ) : (
              <ArenaAlert tone="warning" icon="ph-bold ph-question" title="No encontramos evidencia suficiente para explicar la causa">
                {alert.cause.reason} Preferimos decirlo antes que adivinar: las consultas revisadas están en "Cómo llegué aquí".
              </ArenaAlert>
            )}
          </ArenaSection>

          {alert.cause.kind === 'identified' ? (
            <ArenaSection title="Evidencia" headingLevel="h3">
              <ul className="arena-stack evidence-list">
                {alert.cause.evidence.map((e) => (
                  <Proof key={e.queryId + e.claim.text} evidence={e} />
                ))}
              </ul>
            </ArenaSection>
          ) : null}

          {alert.mergedAlerts?.length ? (
            <ArenaSection
              title="Alertas con la misma causa"
              headingLevel="h3"
              description="Se unieron a esta porque la misma causa las explica. Su evidencia lo prueba."
            >
              <ul className="arena-stack">
                {alert.mergedAlerts.map((m) => (
                  <Merged key={m.id} alert={m} />
                ))}
              </ul>
            </ArenaSection>
          ) : null}

          {pending && alert.actions.length > 0 ? (
            <ArenaSection
              title="Acciones propuestas"
              headingLevel="h3"
              description={alert.actions.length > 1 ? 'Elige una, revísala y apruébala, edítala o rechaza la propuesta.' : undefined}
            >
              <ProposedActions key={alert.id} alert={alert} />
            </ArenaSection>
          ) : null}

          <HowIGotHere alert={alert} />
        </>
      )}
    </article>
  );
}
