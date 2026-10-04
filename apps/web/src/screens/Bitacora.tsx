import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArenaErrorState,
  ArenaPageHead,
  ArenaSelect,
  ArenaSkeleton,
  ArenaTable,
  ArenaTableCell,
  ArenaTableRow,
  ArenaTag,
  type ArenaTableColumn,
} from '@dravensoft/arena-react';
import { ApiError, listAlerts, listBitacora } from '../api/client';
import type { Actor, Agent, Alert, LogEvent, LogEventType } from '../api/types';
import { useSimulation } from '../state/Simulation';
import { formatShortDate, formatShortDateTime } from '../format';

const PAGE_SIZE = 10;

const EVENT: Record<LogEventType, string> = {
  alert: 'Detección',
  evidence: 'Evidencia',
  proposal: 'Propuesta',
  decision: 'Decisión',
  action: 'Acción',
  result: 'Resultado',
  question: 'Pregunta',
  answer: 'Respuesta',
  refusal: 'Pregunta rechazada',
};

const STAGE: Record<Agent, string> = {
  vigia: 'detección',
  analista: 'análisis',
  estratega: 'propuesta',
  ejecutor: 'ejecución',
  chat: 'chat',
};

const COLUMNS: ArenaTableColumn[] = [
  { header: 'Registrado (hora real)', width: 'calc(var(--sp-1) * 32)' },
  { header: 'Día de la operación', mono: true, width: 'calc(var(--sp-1) * 28)' },
  { header: 'Alerta' },
  { header: 'Evento' },
  { header: 'Quién' },
  { header: 'Detalle' },
  { header: 'Fuente', mobileLayout: 'block', width: 'calc(var(--sp-1) * 40)' },
];

function who(actor: Actor): string {
  return actor.kind === 'agent' ? `Centinela · ${STAGE[actor.agent]}` : `${actor.name} (${actor.role})`;
}

function SourceButton({ queryId, open }: { queryId: string; open: (id: string) => void }) {
  return (
    <button type="button" className="link" onClick={() => open(queryId)}>
      Ver de dónde sale
    </button>
  );
}

export function Bitacora() {
  const navigate = useNavigate();
  const { version, openQuery } = useSimulation();
  const [alertId, setAlertId] = useState('');
  const [type, setType] = useState<LogEventType | ''>('');
  const [page, setPage] = useState(1);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [events, setEvents] = useState<LogEvent[] | null>(null);

  const [failure, setFailure] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    listAlerts().then(setAlerts, () => setAlerts([]));
  }, [version, attempt]);

  useEffect(() => {
    setFailure(null);
    listBitacora({ ...(alertId ? { alertId } : {}), ...(type ? { type } : {}) }).then(setEvents, (e: unknown) => {
      if (!(e instanceof ApiError && e.status === 401)) {
        setFailure(e instanceof Error ? e.message : 'No se pudo cargar la bitácora.');
      }
    });
  }, [alertId, type, version, attempt]);

  const titles = new Map(alerts.map((a) => [a.id, a.title.text]));
  const visible = events?.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) ?? [];

  return (
    <div className="arena-band page arena-stack arena-stack--section">
      <ArenaPageHead title="Bitácora" subtitle="Cada detección, propuesta, decisión, resultado y pregunta al chat, del más reciente al más antiguo" />
      <div className="filters">
        <ArenaSelect
          label="Alerta"
          options={[{ value: '', label: 'Todas las alertas' }, ...alerts.map((a) => ({ value: a.id, label: a.title.text }))]}
          value={alertId}
          onChange={(value) => {
            setAlertId(value);
            setPage(1);
          }}
        />
        <ArenaSelect
          label="Tipo de evento"
          options={[{ value: '', label: 'Todos los eventos' }, ...Object.entries(EVENT).map(([value, label]) => ({ value, label }))]}
          value={type}
          onChange={(value) => {
            setType(value as LogEventType | '');
            setPage(1);
          }}
        />
      </div>
      {failure !== null && events === null ? (
        <ArenaErrorState
          headingLevel="h2"
          title="No pudimos cargar la bitácora"
          message={failure}
          retryLabel="Reintentar"
          onRetry={() => setAttempt((n) => n + 1)}
        />
      ) : events === null ? (
        <ArenaSkeleton variant="text" lines={10} />
      ) : (
        <ArenaTable
          label="Eventos de la bitácora"
          columns={COLUMNS}
          page={{ index: page, size: PAGE_SIZE, total: events.length }}
          onPageChange={setPage}
          empty="Ningún evento coincide con estos filtros."
        >
          {visible.map((e) => (
            <ArenaTableRow key={e.id}>
              <ArenaTableCell>{formatShortDateTime(e.date)}</ArenaTableCell>
              <ArenaTableCell>{formatShortDate(e.simulatedDay)}</ArenaTableCell>
              {e.alertId ? (
                <ArenaTableCell href={`/alertas/${e.alertId}`} onNavigate={() => navigate(`/alertas/${e.alertId}`)}>
                  {titles.get(e.alertId) ?? e.alertId}
                </ArenaTableCell>
              ) : (
                <ArenaTableCell>
                  <span className="text-muted">Chat, sin alerta</span>
                </ArenaTableCell>
              )}
              <ArenaTableCell>
                <ArenaTag>{EVENT[e.type]}</ArenaTag>
              </ArenaTableCell>
              <ArenaTableCell>{who(e.actor)}</ArenaTableCell>
              <ArenaTableCell>{e.detail}</ArenaTableCell>
              <ArenaTableCell>
                {e.queryId ? <SourceButton queryId={e.queryId} open={openQuery} /> : <span className="text-muted">Sin cifras</span>}
              </ArenaTableCell>
            </ArenaTableRow>
          ))}
        </ArenaTable>
      )}
    </div>
  );
}
