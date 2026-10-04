import { useState } from 'react';
import { ArenaButton } from '@dravensoft/arena-react';
import type { Alert } from '../api/types';
import { SentenceWithFigures, LinkedFigure } from '../common/SentenceWithFigures';
import { Confidence } from '../common/Badges';
import { formatDate } from '../format';
import '../styles/agent-phases.css';

interface AgentPhase {
  agent: 'vigia' | 'analista' | 'estratega' | 'ejecutor';
  name: string;
  icon: string;
  color: string;
}

const PHASES: AgentPhase[] = [
  {
    agent: 'vigia',
    name: 'Vigía - Detección',
    icon: 'ph-bold ph-eye',
    color: 'var(--color-vigia, #6366f1)',
  },
  {
    agent: 'analista',
    name: 'Analista - Causa Raíz',
    icon: 'ph-bold ph-magnifying-glass',
    color: 'var(--color-analista, #8b5cf6)',
  },
  {
    agent: 'estratega',
    name: 'Estratega - Propuesta',
    icon: 'ph-bold ph-lightbulb',
    color: 'var(--color-estratega, #d946ef)',
  },
  {
    agent: 'ejecutor',
    name: 'Ejecutor - Acción',
    icon: 'ph-bold ph-check-circle',
    color: 'var(--color-ejecutor, #ec4899)',
  },
];

function PhaseContent({ alert, phase }: { alert: Alert; phase: AgentPhase }) {
  switch (phase.agent) {
    case 'vigia':
      return (
        <div className="agent-phase__content arena-stack arena-stack--group">
          <div className="agent-phase__field">
            <label className="agent-phase__label">
              <i className="ph-bold ph-chart-bar" />
              Métrica Detectada
            </label>
            <p className="agent-phase__value font-semibold">{alert.metric}</p>
          </div>

          <div className="agent-phase__field">
            <label className="agent-phase__label">
              <i className="ph-bold ph-text-t" />
              Descripción
            </label>
            <div className="agent-phase__value">
              <SentenceWithFigures text={alert.title.text} figures={alert.title.figures} />
            </div>
          </div>

          <div className="agent-phase__field">
            <label className="agent-phase__label">
              <i className="ph-bold ph-calendar" />
              Fecha de Detección
            </label>
            <p className="agent-phase__value">{formatDate(alert.simulatedDate)}</p>
          </div>

          <div className="agent-phase__field">
            <label className="agent-phase__label">
              <i className="ph-bold ph-warning" />
              Exposición en Riesgo
            </label>
            <div className="agent-phase__money">
              <LinkedFigure figure={alert.pesosAtRisk} />
            </div>
          </div>

          {alert.labels && alert.labels.length > 0 && (
            <div className="agent-phase__field">
              <label className="agent-phase__label">
                <i className="ph-bold ph-tag" />
                Identidad
              </label>
              <div className="agent-phase__labels">
                {alert.labels.map((label) => (
                  <span key={label} className="arena-badge arena-badge--neutral">
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="agent-phase__status">
            <i className="ph-bold ph-check-circle" />
            <p>Detección completada: análisis de datos brutos</p>
          </div>
        </div>
      );

    case 'analista':
      return (
        <div className="agent-phase__content arena-stack arena-stack--group">
          {alert.cause.kind === 'identified' ? (
            <>
              <div className="agent-phase__field">
                <label className="agent-phase__label">
                  <i className="ph-bold ph-magnifying-glass" />
                  Causa Identificada
                </label>
                <div className="agent-phase__value font-semibold">
                  <SentenceWithFigures text={alert.cause.sentence.text} figures={alert.cause.sentence.figures} />
                </div>
              </div>

              {alert.cause.evidence && alert.cause.evidence.length > 0 && (
                <div className="agent-phase__field">
                  <label className="agent-phase__label">
                    <i className="ph-bold ph-list-checks" />
                    Evidencia ({alert.cause.evidence.length} consulta{alert.cause.evidence.length !== 1 ? 's' : ''})
                  </label>
                  <ul className="agent-phase__evidence">
                    {alert.cause.evidence.map((e, i) => (
                      <li key={e.queryId} className="agent-phase__evidence-item">
                        <span className="agent-phase__evidence-num">{i + 1}</span>
                        <div className="arena-stack">
                          <p>
                            <SentenceWithFigures text={e.claim.text} figures={e.claim.figures} />
                          </p>
                          <p className="text-muted text-sm">Query ID: {e.queryId}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {alert.confidence.assumptions && alert.confidence.assumptions.length > 0 && (
                <div className="agent-phase__field">
                  <label className="agent-phase__label">
                    <i className="ph-bold ph-info" />
                    Supuestos
                  </label>
                  <ul className="agent-phase__assumptions">
                    {alert.confidence.assumptions.map((assumption, i) => (
                      <li key={i}>
                        <span className="text-muted">•</span> {assumption}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="agent-phase__field">
                <label className="agent-phase__label">
                  <i className="ph-bold ph-gauge" />
                  Confianza del Análisis
                </label>
                <div className="agent-phase__confidence">
                  <Confidence level={alert.confidence.level} />
                  <p className="text-muted text-sm">
                    {alert.confidence.level === 'high'
                      ? 'Alta confianza en la causa identificada'
                      : alert.confidence.level === 'medium'
                        ? 'Confianza moderada en la causa identificada'
                        : 'Baja confianza - revisar manualmente'}
                  </p>
                </div>
              </div>

              <div className="agent-phase__status">
                <i className="ph-bold ph-check-circle" />
                <p>Análisis completado: causa raíz identificada</p>
              </div>
            </>
          ) : (
            <div className="agent-phase__no-result">
              <i className="ph-bold ph-warning" />
              <div>
                <h4>Causa No Identificada</h4>
                <p>{alert.cause.reason}</p>
              </div>
            </div>
          )}
        </div>
      );

    case 'estratega':
      return (
        <div className="agent-phase__content arena-stack arena-stack--group">
          {alert.actions && alert.actions.length > 0 ? (
            <>
              <div className="agent-phase__field">
                <label className="agent-phase__label">
                  <i className="ph-bold ph-lightning" />
                  Acciones Propuestas ({alert.actions.length})
                </label>
                <ul className="agent-phase__actions">
                  {alert.actions.map((action, i) => (
                    <li key={action.id} className="agent-phase__action-item">
                      <div className="agent-phase__action-header">
                        <span className="agent-phase__action-num">{i + 1}</span>
                        <span className="font-semibold">{action.title}</span>
                        <span className="arena-badge arena-badge--secondary text-xs">{action.type}</span>
                      </div>
                      {typeof action.description === 'string' && action.description && (
                        <p className="text-sm">{action.description}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="agent-phase__field">
                <label className="agent-phase__label">
                  <i className="ph-bold ph-trending-up" />
                  Impacto Recuperable
                </label>
                {alert.recoverablePerMonth ? (
                  <div className="agent-phase__recoverable">
                    <LinkedFigure figure={alert.recoverablePerMonth} />
                    <span>por mes</span>
                  </div>
                ) : (
                  <p className="text-muted">No calculado</p>
                )}
              </div>

              <div className="agent-phase__status">
                <i className="ph-bold ph-check-circle" />
                <p>Estrategia completada: acciones diseñadas según políticas</p>
              </div>
            </>
          ) : (
            <div className="agent-phase__no-result">
              <i className="ph-bold ph-hand-pointing" />
              <div>
                <h4>Decisión Manual Requerida</h4>
                <p>El sistema determinó que esta alerta requiere decisión manual del usuario.</p>
              </div>
            </div>
          )}
        </div>
      );

    case 'ejecutor':
      return (
        <div className="agent-phase__content arena-stack arena-stack--group">
          {alert.executedAction ? (
            <>
              <div className="agent-phase__field">
                <label className="agent-phase__label">
                  <i className="ph-bold ph-check-circle" />
                  Acción Ejecutada
                </label>
                <p className="agent-phase__value font-semibold">{alert.executedAction.actionId}</p>
              </div>

              {alert.executedAction.result && (
                <div className="agent-phase__field">
                  <label className="agent-phase__label">
                    <i className="ph-bold ph-note-pencil" />
                    Resultado
                  </label>
                  <p className="agent-phase__value text-sm">{alert.executedAction.result}</p>
                </div>
              )}

              <div className="agent-phase__status">
                <i className="ph-bold ph-check-circle" />
                <p>Ejecución completada exitosamente</p>
              </div>
            </>
          ) : (
            <div className="agent-phase__no-result">
              <i className="ph-bold ph-clock" />
              <div>
                <h4>Pendiente de Aprobación</h4>
                <p>Esperando que el usuario apruebe una de las acciones propuestas por el estratega.</p>
              </div>
            </div>
          )}
        </div>
      );

    default:
      return null;
  }
}

export function AgentPhasesModal({ alert, isOpen, onClose }: { alert: Alert; isOpen: boolean; onClose: () => void }) {
  const [expandedIndex, setExpandedIndex] = useState(0);

  if (!isOpen) return null;

  return (
    <div className="agent-phases-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="agent-phases-modal-wrapper arena-stack" role="dialog" aria-labelledby="phases-title">
        <div className="agent-phases-header">
          <div className="arena-stack arena-stack--group" style={{ gap: '0.5rem' }}>
            <h2 id="phases-title" style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
              <i className="ph-bold ph-flow-arrow" />
              Fases del Análisis
            </h2>
            <p className="text-muted" style={{ margin: 0, fontSize: '0.875rem' }}>
              Flujo del análisis a través de cada agente del sistema
            </p>
          </div>
          <button
            className="agent-phases-close"
            onClick={onClose}
            aria-label="Cerrar"
            type="button"
          >
            <i className="ph-bold ph-x" />
          </button>
        </div>

        <div className="agent-phases-timeline">
          <div className="agent-phases-timeline__track" />
          {PHASES.map((phase) => (
            <div key={phase.agent} className="agent-phases-timeline__step">
              <div
                className="agent-phases-timeline__dot"
                style={{ backgroundColor: phase.color }}
                title={phase.name}
              />
            </div>
          ))}
        </div>

        <div className="agent-phases-accordion arena-stack">
          {PHASES.map((phase, index) => (
            <div key={phase.agent} className="agent-phases-accordion__item">
              <button
                className={`agent-phases-accordion__trigger ${expandedIndex === index ? 'is-open' : ''}`}
                onClick={() => setExpandedIndex(expandedIndex === index ? -1 : index)}
                aria-expanded={expandedIndex === index}
              >
                <span className="agent-phases-accordion__icon" style={{ color: phase.color }}>
                  <i className="ph-bold ph-caret-down" />
                </span>
                <span className="agent-phases-accordion__title">{phase.name}</span>
              </button>
              {expandedIndex === index && (
                <div className="agent-phases-accordion__content">
                  <PhaseContent alert={alert} phase={phase} />
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="agent-phases-footer arena-stack arena-stack--group">
          <p className="text-muted text-sm">
            <i className="ph-bold ph-lightbulb" />
            <span>Cada fase construye sobre la anterior. Revisa los detalles en orden para entender las decisiones.</span>
          </p>
          <ArenaButton onClick={onClose}>
            Cerrar
          </ArenaButton>
        </div>
      </div>
    </div>
  );
}
