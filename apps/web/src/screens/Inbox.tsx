import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  ArenaButton,
  ArenaDialog,
  ArenaEmptyState,
  ArenaErrorState,
  ArenaPageHead,
  ArenaSegmentedControl,
  ArenaSkeleton,
  ArenaStatCard,
  arenaReadBreakpoint,
  useArenaContainerWidth,
  useArenaViewportBelow,
} from '@dravensoft/arena-react';
import { ApiError, getInboxSummary, listAlerts } from '../api/client';
import type { Alert, InboxSummary } from '../api/types';
import { useSimulation } from '../state/Simulation';
import { fillSentence, formatCompactPesos, formatDate, formatNumber, formatPesos } from '../format';
import { AlertDetail } from './AlertDetail';
import { AlertList } from './AlertList';

type Filter = 'pending' | 'decided' | 'all';

const FILTERS = [
  { value: 'pending', label: 'Por decidir' },
  { value: 'decided', label: 'Decididas' },
  { value: 'all', label: 'Todas' },
];

const DECIDED: Alert['status'][] = ['approved', 'rejected', 'executed'];

function passesFilter(alert: Alert, filter: Filter): boolean {
  const decided = DECIDED.includes(alert.status);
  return filter === 'all' || (filter === 'decided' ? decided : !decided);
}

function alertName(alert: Alert): string {
  return alert.labels.length > 0
    ? alert.labels.join(' · ')
    : fillSentence(alert.title.text, alert.title.figures);
}

type AmountKey = 'pesosAtRisk' | 'recoverablePerMonth';

const AMOUNT_DESCRIPTION: Record<AmountKey, string> = {
  pesosAtRisk: 'Suma de pesos en riesgo de las alertas por decidir',
  recoverablePerMonth: 'Suma del importe recuperable al mes de las alertas por decidir',
};

function AlertsAmountDialog({
  open,
  alerts,
  amountKey,
  onClose,
}: {
  open: boolean;
  alerts: Alert[] | null;
  amountKey: AmountKey;
  onClose: () => void;
}) {
  const { simulatedDay } = useSimulation();
  const rows = (alerts ?? [])
    .filter((a) => a[amountKey] != null)
    .sort((a, b) => (b[amountKey]?.value ?? 0) - (a[amountKey]?.value ?? 0));

  const description = AMOUNT_DESCRIPTION[amountKey] + (simulatedDay ? `, ${formatDate(simulatedDay)}` : '');

  return (
    <ArenaDialog
      open={open}
      eyebrow="Cómo llegué aquí"
      title="De dónde sale esta cifra"
      width="calc(var(--sp-1) * 140)"
      fillBelow="sm"
      onClose={onClose}
      footer={
        <ArenaButton variant="secondary" onClick={onClose}>
          Cerrar
        </ArenaButton>
      }
    >
      <div className="arena-stack arena-stack--group query">
        <p className="query__description">{description}</p>
        {rows.length === 0 ? (
          <p className="text-muted">No hay alertas con este importe actualmente.</p>
        ) : (
          <div className="query__table-wrap">
            <table className="query__table">
              <thead>
                <tr>
                  <th scope="col">Alerta</th>
                  <th scope="col">Importe</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((alert) => (
                  <tr key={alert.id}>
                    <td>{alertName(alert)}</td>
                    <td className="arena-num">{formatPesos(alert[amountKey]?.value ?? 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="text-muted query__source">Fuente: registro de alertas de Centinela</p>
      </div>
    </ArenaDialog>
  );
}

function MonetaryTotal({
  label,
  value,
  sub,
  alerts,
  amountKey,
}: {
  label: string;
  value: string;
  sub: string;
  alerts: Alert[] | null;
  amountKey: AmountKey;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="arena-stack arena-stack--group total">
      <ArenaStatCard label={label} value={value} sub={sub} />
      <button type="button" className="link" onClick={() => setOpen(true)}>
        Ver por alerta<span className="arena-sr-only"> {label.toLowerCase()}</span>
      </button>
      <AlertsAmountDialog
        open={open}
        alerts={alerts}
        amountKey={amountKey}
        onClose={() => setOpen(false)}
      />
    </div>
  );
}

function CountTotal({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="arena-stack arena-stack--group total">
      <ArenaStatCard label={label} value={value} sub={sub} />
    </div>
  );
}

function CompactTotals({ summary, alerts }: { summary: InboxSummary; alerts: Alert[] | null }) {
  const [openDialog, setOpenDialog] = useState<AmountKey | null>(null);
  return (
    <>
      <dl className="totals-compact">
        <div>
          <dt className="eyebrow">En riesgo hoy</dt>
          <dd>
            <button type="button" className="figure-link" onClick={() => setOpenDialog('pesosAtRisk')}>
              {formatCompactPesos(summary.moneyAtRisk.value)}
              <span className="arena-sr-only">, ver por alerta</span>
            </button>
          </dd>
        </div>
        <div>
          <dt className="eyebrow">Por decidir</dt>
          <dd>
            <span className="arena-num">{formatNumber(summary.pendingDecisions.value)}</span>
          </dd>
        </div>
        <div>
          <dt className="eyebrow">Recuperable al mes</dt>
          <dd>
            <button type="button" className="figure-link" onClick={() => setOpenDialog('recoverablePerMonth')}>
              {formatCompactPesos(summary.recoverablePerMonth.value)}
              <span className="arena-sr-only">, ver por alerta</span>
            </button>
          </dd>
        </div>
      </dl>
      <AlertsAmountDialog
        open={openDialog !== null}
        alerts={alerts}
        amountKey={openDialog ?? 'pesosAtRisk'}
        onClose={() => setOpenDialog(null)}
      />
    </>
  );
}

export function Inbox() {
  const { id } = useParams();
  const [band, width] = useArenaContainerWidth<HTMLDivElement>();
  const mobile = useArenaViewportBelow('lg') || (width !== null && width < arenaReadBreakpoint('md'));
  const narrow = useArenaViewportBelow('sm');
  const { simulatedDay, atLastDay, version, advance, advancing } = useSimulation();
  const [filter, setFilter] = useState<Filter>('pending');
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [summary, setSummary] = useState<InboxSummary | null>(null);

  const [failure, setFailure] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setFailure(null);
    Promise.all([listAlerts(), getInboxSummary()]).then(
      ([loaded, totals]) => {
        setAlerts(loaded);
        setSummary(totals);
      },
      (e: unknown) => {
        if (!(e instanceof ApiError && e.status === 401)) {
          setFailure(e instanceof Error ? e.message : 'No se pudo cargar la bandeja.');
        }
      },
    );
  }, [version, attempt]);

  if (mobile && id) {
    return (
      <div ref={band} className="arena-band page">
        <AlertDetail id={id} alone />
      </div>
    );
  }

  if (failure !== null && alerts === null) {
    return (
      <div className="arena-band page">
        <ArenaErrorState
          title="No pudimos cargar la bandeja"
          message={failure}
          retryLabel="Reintentar"
          onRetry={() => setAttempt((n) => n + 1)}
        />
      </div>
    );
  }

  const visible = alerts?.filter((a) => passesFilter(a, filter)) ?? null;
  const pendingAlerts = alerts?.filter((a) => !DECIDED.includes(a.status)) ?? null;

  return (
    <div ref={band} className="arena-band page arena-stack arena-stack--section">
      <ArenaPageHead
        title="Bandeja de decisiones"
        subtitle={simulatedDay ? `Situación al ${formatDate(simulatedDay)}` : undefined}
      />
      {summary && narrow ? (
        <CompactTotals summary={summary} alerts={pendingAlerts} />
      ) : summary ? (
        <div className="totals">
          <MonetaryTotal
            label="En riesgo hoy"
            value={formatPesos(summary.moneyAtRisk.value)}
            sub="en las alertas por decidir"
            alerts={pendingAlerts}
            amountKey="pesosAtRisk"
          />
          <CountTotal
            label="Por decidir"
            value={formatNumber(summary.pendingDecisions.value)}
            sub={summary.pendingDecisions.value === 1 ? 'decisión espera tu aprobación' : 'decisiones esperan tu aprobación'}
          />
          <MonetaryTotal
            label="Recuperable al mes"
            value={formatPesos(summary.recoverablePerMonth.value)}
            sub={
              summary.recoverablePerMonth.value === 0
                ? 'ninguna propuesta pendiente estima una recuperación mensual'
                : 'si apruebas lo propuesto'
            }
            alerts={pendingAlerts}
            amountKey="recoverablePerMonth"
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
                  : atLastDay
                    ? 'Todos los indicadores vigilados están dentro de sus umbrales, y los datos llegan hasta este día.'
                    : 'Todos los indicadores vigilados están dentro de sus umbrales. Avanza el día para revisar el siguiente.'
              }
              action={
                filter === 'decided' || atLastDay ? undefined : (
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
              <AlertDetail id={id} alone={false} />
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
