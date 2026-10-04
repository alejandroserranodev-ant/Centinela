import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArenaAlert,
  ArenaButton,
  ArenaErrorState,
  ArenaSection,
  ArenaSkeleton,
  ArenaSpinner,
} from '@dravensoft/arena-react';
import { ApiError, getAlert, getQuery, listBitacora } from '../api/client';
import type { Alert, Evidence, LogEvent, MergedAlert, Query } from '../api/types';
import { latestResult } from '../logEvent';
import { explainedByRemaining } from '../alert';
import { Confidence, Labels, Severity, Status } from '../common/Badges';
import { LinkedFigure, SentenceWithFigures } from '../common/SentenceWithFigures';
import { SeriesChart, sourceTitle } from '../common/SeriesChart';
import { useSimulation } from '../state/Simulation';
import { fillSentence, formatDate } from '../format';
import { HowIGotHere } from './HowIGotHere';
import { ProposedActions } from './ProposedActions';
import { AgentPhasesModal } from './AgentPhasesModal';

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
      ) : explainedByRemaining(alert.cause, true) ? null : (
        <p>{alert.cause.reason}</p>
      )}
    </li>
  );
}

function NotExecuted({ alert }: { alert: Alert }) {
  const [result, setResult] = useState<LogEvent | null | undefined>(undefined);
  useEffect(() => {
    setResult(undefined);
    listBitacora({ alertId: alert.id, type: 'result' }).then((events) => setResult(latestResult(events)), () => setResult(null));
  }, [alert.id, alert.status]);
  if (result) {
    return (
      <ArenaAlert tone="warning" title="Aprobada, sin ejecutar">
        {result.detail}
      </ArenaAlert>
    );
  }
  return (
    <ArenaAlert tone="success" title="Aprobada">
      {result === undefined ? 'Revisando el resultado de la acción…' : 'La acción está en curso.'}
    </ArenaAlert>
  );
}

function Remaining({ id }: { id: string }) {
  const [title, setTitle] = useState<string | null>(null);
  useEffect(() => {
    setTitle(null);
    getAlert(id).then((a) => setTitle(fillSentence(a.title.text, a.title.figures)), () => setTitle(null));
  }, [id]);
  return title ? <>«{title}»</> : <>la alerta que queda</>;
}

function Outcome({ alert, onOpen }: { alert: Alert; onOpen: (id: string) => void }) {
  if (alert.status === 'approved' && !alert.executedAction) {
    return <NotExecuted alert={alert} />;
  }
  if (alert.status === 'merged' && alert.mergedInto) {
    const into = alert.mergedInto;
    return (
      <ArenaAlert tone="info" title="Unida a otra alerta" actionLabel="Ver la alerta que queda" onAction={() => onOpen(into)}>
        La misma causa explica las dos, así que se decide en <Remaining id={into} />. Esta no espera ninguna decisión.
      </ArenaAlert>
    );
  }
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

export function AlertDetail({ id, alone }: { id: string; alone: boolean }) {
  const navigate = useNavigate();
  const { version, openChat } = useSimulation();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [failure, setFailure] = useState<Error | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [phasesModalOpen, setPhasesModalOpen] = useState(false);

  useEffect(() => {
    setFailure(null);
    getAlert(id).then(setAlert, (e: unknown) => {
      if (!(e instanceof ApiError && e.status === 401)) {
        setFailure(e instanceof Error ? e : new Error('No se pudo cargar la alerta.'));
      }
    });
  }, [id, version, attempt]);

  useEffect(() => {
    setAlert(null);
  }, [id]);

  const back = alone ? (
    <div>
      <ArenaButton variant="ghost" size="sm" icon="ph-bold ph-arrow-left" onClick={() => navigate('/')}>
        Volver a la bandeja
      </ArenaButton>
    </div>
  ) : null;

  if (failure && !(failure instanceof ApiError && failure.status === 404)) {
    return (
      <div className="arena-stack">
        {back}
        <ArenaErrorState
          title="No pudimos cargar la alerta"
          message={failure.message}
          retryLabel="Reintentar"
          onRetry={() => setAttempt((n) => n + 1)}
        />
      </div>
    );
  }

  if (failure) {
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
        <div className="arena-row" style={{ gap: '0.5rem', flexWrap: 'wrap' }}>
          <ArenaButton variant="ghost" size="sm" icon="ph-bold ph-chat-circle-text" onClick={() => openChat(alert.id)}>
            Preguntar sobre esta alerta
          </ArenaButton>
          <ArenaButton variant="secondary" size="sm" icon="ph-bold ph-flow-arrow" onClick={() => setPhasesModalOpen(true)}>
            Ver fases de análisis
          </ArenaButton>
        </div>
      </header>

      <Outcome alert={alert} onOpen={(into) => navigate(`/alertas/${into}`)} />

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
            ) : explainedByRemaining(alert.cause, alert.status === 'merged') ? (
              <p>La causa está en la alerta que queda, que la explica con su evidencia.</p>
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
              description={alert.canDecide && alert.actions.length > 1 ? 'Elige una, revísala y apruébala, edítala o rechaza la propuesta.' : undefined}
            >
              <ProposedActions key={alert.id} alert={alert} />
            </ArenaSection>
          ) : null}

          <HowIGotHere alert={alert} />
        </>
      )}

      {alert && <AgentPhasesModal alert={alert} isOpen={phasesModalOpen} onClose={() => setPhasesModalOpen(false)} />}
    </article>
  );
}
