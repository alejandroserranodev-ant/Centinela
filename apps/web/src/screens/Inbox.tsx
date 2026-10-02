import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  ArenaButton,
  ArenaEmptyState,
  ArenaPageHead,
  ArenaSegmentedControl,
  ArenaSkeleton,
  ArenaStatCard,
  useArenaViewportBelow,
} from '@dravensoft/arena-react';
import { getInboxSummary, listAlerts } from '../api/client';
import type { Alert, Figure, InboxSummary } from '../api/types';
import { useSimulation } from '../state/Simulation';
import { formatCompactPesos, formatDate, formatNumber, formatPesos } from '../format';
import { AlertDetail } from './AlertDetail';
import { AlertList } from './AlertList';

type Filter = 'pending' | 'decided' | 'all';

const FILTERS = [
  { value: 'pending', label: 'Por decidir' },
  { value: 'decided', label: 'Decididas' },
  { value: 'all', label: 'Todas' },
];

const DECIDED: Alert['status'][] = ['approved', 'rejected', 'executed', 'merged'];

function passesFilter(alert: Alert, filter: Filter): boolean {
  const decided = DECIDED.includes(alert.status);
  return filter === 'all' || (filter === 'decided' ? decided : !decided);
}

function Total({ label, value, sub, figure }: { label: string; value: string; sub: string; figure: Figure }) {
  const { openQuery } = useSimulation();
  return (
    <div className="arena-stack arena-stack--group total">
      <ArenaStatCard label={label} value={value} sub={sub} />
      <button type="button" className="link" onClick={() => openQuery(figure.queryId)}>
        Ver de dónde sale<span className="arena-sr-only"> {label.toLowerCase()}</span>
      </button>
    </div>
  );
}

function CompactTotals({ summary }: { summary: InboxSummary }) {
  const { openQuery } = useSimulation();
  const totals = [
    { label: 'En riesgo hoy', value: formatCompactPesos(summary.moneyAtRisk.value), figure: summary.moneyAtRisk },
    { label: 'Por decidir', value: formatNumber(summary.pendingDecisions.value), figure: summary.pendingDecisions },
    {
      label: 'Recuperable al mes',
      value: formatCompactPesos(summary.recoverablePerMonth.value),
      figure: summary.recoverablePerMonth,
    },
  ];
  return (
    <dl className="totals-compact">
      {totals.map((t) => (
        <div key={t.label}>
          <dt className="eyebrow">{t.label}</dt>
          <dd>
            <button type="button" className="figure-link" onClick={() => openQuery(t.figure.queryId)}>
              {t.value}
              <span className="arena-sr-only">, ver de dónde sale</span>
            </button>
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function Inbox() {
  const { id } = useParams();
  const mobile = useArenaViewportBelow('lg');
  const narrow = useArenaViewportBelow('sm');
  const { simulatedDay, version, advance, advancing } = useSimulation();
  const [filter, setFilter] = useState<Filter>('pending');
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [summary, setSummary] = useState<InboxSummary | null>(null);

  useEffect(() => {
    listAlerts().then(setAlerts);
    getInboxSummary().then(setSummary);
  }, [version]);

  if (mobile && id) {
    return (
      <div className="arena-band page">
        <AlertDetail id={id} />
      </div>
    );
  }

  const visible = alerts?.filter((a) => passesFilter(a, filter)) ?? null;

  return (
    <div className="arena-band page arena-stack arena-stack--section">
      <ArenaPageHead
        title="Bandeja de decisiones"
        subtitle={simulatedDay ? `Situación al ${formatDate(simulatedDay)}` : undefined}
      />
      {summary && narrow ? (
        <CompactTotals summary={summary} />
      ) : summary ? (
        <div className="totals">
          <Total
            label="En riesgo hoy"
            value={formatPesos(summary.moneyAtRisk.value)}
            sub="en las alertas por decidir"
            figure={summary.moneyAtRisk}
          />
          <Total
            label="Por decidir"
            value={formatNumber(summary.pendingDecisions.value)}
            sub={summary.pendingDecisions.value === 1 ? 'decisión espera tu aprobación' : 'decisiones esperan tu aprobación'}
            figure={summary.pendingDecisions}
          />
          <Total
            label="Recuperable al mes"
            value={formatPesos(summary.recoverablePerMonth.value)}
            sub={
              summary.recoverablePerMonth.value === 0
                ? 'ninguna propuesta pendiente estima una recuperación mensual'
                : 'si apruebas lo propuesto'
            }
            figure={summary.recoverablePerMonth}
          />
        </div>
      ) : (
        <ArenaSkeleton variant="block" height="calc(var(--sp-1) * 28)" />
      )}
      <div className={mobile ? 'inbox' : 'inbox inbox--reading'}>
        <section className="arena-stack inbox__list" aria-label="Alertas">
          <ArenaSegmentedControl
            ariaLabel="Estado de las alertas"
            size="sm"
            options={FILTERS}
            value={filter}
            onChange={(value) => setFilter(value as Filter)}
          />
          {visible === null ? (
            <ArenaSkeleton variant="text" lines={6} />
          ) : visible.length === 0 ? (
            <ArenaEmptyState
              icon="ph-bold ph-check-circle"
              headingLevel="h2"
              title={filter === 'decided' ? 'Aún no hay decisiones tomadas' : 'No hay decisiones pendientes'}
              message={
                filter === 'decided'
                  ? 'Lo que apruebes o rechaces queda aquí y en la bitácora.'
                  : 'Todos los indicadores vigilados están dentro de sus umbrales. Avanza el día para revisar el siguiente.'
              }
              action={
                filter === 'decided' ? undefined : (
                  <ArenaButton variant="secondary" icon="ph-bold ph-fast-forward" loading={advancing} onClick={advance}>
                    Avanzar un día
                  </ArenaButton>
                )
              }
            />
          ) : (
            <AlertList alerts={visible} selected={id} />
          )}
        </section>
        {mobile ? null : (
          <section className="inbox__column" aria-label="Detalle de la alerta">
            {id ? (
              <AlertDetail id={id} />
            ) : (
              <ArenaEmptyState
                icon="ph-bold ph-cursor-click"
                headingLevel="h2"
                title="Elige una alerta"
                message="Su explicación, la evidencia y las acciones propuestas aparecen aquí. Usa las flechas para recorrer la lista."
              />
            )}
          </section>
        )}
      </div>
    </div>
  );
}
