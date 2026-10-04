import { useRef, type KeyboardEvent } from 'react';
import { Link } from 'react-router-dom';
import type { Alert } from '../api/types';
import { Confidence, Labels, Severity, Status } from '../common/Badges';
import { fillSentence, formatDate, formatPesos } from '../format';

interface Props {
  alerts: Alert[];
  selected?: string;
}

function proposalLine(alert: Alert): string | null {
  if (alert.status === 'proposed') {
    const [first, ...others] = alert.actions;
    if (!first) return null;
    return others.length === 0 ? `Propuesta: ${first.title}` : `Propuesta: ${first.title} y ${others.length} más`;
  }
  const executed = alert.actions.find((a) => a.id === alert.executedAction?.actionId);
  return executed ? `Aprobada: ${executed.title}` : null;
}

export function AlertList({ alerts, selected }: Props) {
  const list = useRef<HTMLUListElement>(null);
  const focusable = alerts.some((a) => a.id === selected) ? selected : alerts[0]?.id;

  const moveFocus = (event: KeyboardEvent<HTMLUListElement>) => {
    const rows = Array.from(list.current?.querySelectorAll<HTMLAnchorElement>('a.alert-row') ?? []);
    const current = rows.indexOf(document.activeElement as HTMLAnchorElement);
    const target: Record<string, number> = {
      ArrowDown: Math.min(current + 1, rows.length - 1),
      ArrowUp: Math.max(current - 1, 0),
      Home: 0,
      End: rows.length - 1,
    };
    if (current < 0 || !(event.key in target)) {
      return;
    }
    event.preventDefault();
    rows.forEach((row, i) => (row.tabIndex = i === target[event.key] ? 0 : -1));
    rows[target[event.key]]?.focus();
  };

  return (
    <ul ref={list} className="alert-list" aria-label="Alertas, de mayor a menor riesgo en pesos" onKeyDown={moveFocus}>
      {alerts.map((alert) => (
        <li key={alert.id}>
          <Link
            to={`/alertas/${alert.id}`}
            className="alert-row"
            tabIndex={alert.id === focusable ? 0 : -1}
            aria-current={alert.id === selected ? 'page' : undefined}
          >
            <span className="arena-row alert-row__head">
              <Severity level={alert.severity} />
              <Labels labels={alert.labels} />
              {alert.status === 'proposed' ? null : <Status status={alert.status} />}
              <time className="text-muted" dateTime={alert.simulatedDate}>
                {formatDate(alert.simulatedDate)}
              </time>
            </span>
            <span className="alert-row__title">{fillSentence(alert.title.text, alert.title.figures)}</span>
            {proposalLine(alert) ? <span className="alert-row__proposal">{proposalLine(alert)}</span> : null}
            <span className="alert-row__figures">
              <span>
                <span className="eyebrow">En riesgo</span> <span className="arena-num">{formatPesos(alert.pesosAtRisk.value)}</span>
              </span>
              {alert.recoverablePerMonth ? (
                <span>
                  <span className="eyebrow">Recuperable</span>{' '}
                  <span className="arena-num">{formatPesos(alert.recoverablePerMonth.value)}</span> al mes
                </span>
              ) : null}
              <Confidence level={alert.confidence.level} />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
