import { useEffect, useState } from 'react';
import {
  ArenaButton,
  ArenaErrorState,
  ArenaInput,
  ArenaPageHead,
  ArenaRadio,
  ArenaRadioGroup,
  ArenaSelect,
  ArenaSkeleton,
  ArenaSwitch,
  ArenaTab,
  ArenaTable,
  ArenaTableCell,
  ArenaTableRow,
  ArenaTabs,
  type ArenaTableColumn,
} from '@dravensoft/arena-react';
import { ApiError, getSettings, saveSettings } from '../api/client';
import type { ActionType, AutonomyLevel, Settings as SettingsData, WatchedMetric } from '../api/types';
import { canConfigure } from '../roles';
import { useSession } from '../state/Session';
import { useSimulation } from '../state/Simulation';

const ACTION_TYPES: { type: ActionType; name: string }[] = [
  { type: 'email_draft', name: 'Borrador de correo' },
  { type: 'task', name: 'Tarea' },
  { type: 'purchase_order_draft', name: 'Borrador de orden de compra' },
  { type: 'price_change_draft', name: 'Borrador de ajuste de precio' },
];

const COLUMNS: ArenaTableColumn[] = [{ header: 'KPI' }, { header: 'Vigilar' }, { header: 'Umbrales' }];

const NO_AREA = '';

type Values = Record<string, string>;

const valueKey = (metric: WatchedMetric['metric'], key: string) => `${metric}.${key}`;

function editableValues(settings: SettingsData): Values {
  return Object.fromEntries(
    settings.metrics.flatMap((m) =>
      m.thresholds.filter((t) => t.editable).map((t) => [valueKey(m.metric, t.key), String(t.value ?? '')]),
    ),
  );
}

function thresholdError(text: string): string | undefined {
  if (text.trim() === '' || !Number.isFinite(Number(text))) {
    return 'Escribe un número';
  }
  return Number(text) < 0 ? 'El umbral no puede ser negativo' : undefined;
}

export function Settings() {
  const { notify } = useSimulation();
  const { persona } = useSession();
  const [tab, setTab] = useState('kpis');
  const [draft, setDraft] = useState<SettingsData | null>(null);
  const [values, setValues] = useState<Values>({});
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const allowed = persona !== null && canConfigure(persona);

  useEffect(() => {
    setFailure(null);
    getSettings().then(
      (data) => {
        setDraft(data);
        setValues(editableValues(data));
      },
      (e: unknown) => {
        if (!(e instanceof ApiError && e.status === 401)) {
          setFailure(e instanceof Error ? e.message : 'No se pudo cargar la configuración.');
        }
      },
    );
  }, [attempt]);

  if (!draft) {
    return (
      <div className="arena-band page arena-stack arena-stack--section">
        <ArenaPageHead title="Configuración" />
        {failure !== null ? (
          <ArenaErrorState
            headingLevel="h2"
            title="No pudimos cargar la configuración"
            message={failure}
            retryLabel="Reintentar"
            onRetry={() => setAttempt((n) => n + 1)}
          />
        ) : (
          <ArenaSkeleton variant="text" lines={8} />
        )}
      </div>
    );
  }

  const changeMetric = (metric: WatchedMetric['metric'], change: Partial<WatchedMetric>) =>
    setDraft({ ...draft, metrics: draft.metrics.map((m) => (m.metric === metric ? { ...m, ...change } : m)) });

  const changeAutonomy = (type: ActionType, level: AutonomyLevel) =>
    setDraft({ ...draft, autonomy: { ...draft.autonomy, [type]: level } });

  const invalid = draft.metrics.some((m) =>
    m.thresholds.some((t) => t.editable && thresholdError(values[valueKey(m.metric, t.key)] ?? '') !== undefined),
  );

  const save = async () => {
    setSaving(true);
    try {
      const next: SettingsData = {
        ...draft,
        metrics: draft.metrics.map((m) => ({
          ...m,
          thresholds: m.thresholds.map((t) => (t.editable ? { ...t, value: Number(values[valueKey(m.metric, t.key)]) } : t)),
        })),
      };
      const saved = await saveSettings(next);
      setDraft(saved);
      setValues(editableValues(saved));
      notify({ tone: 'success', title: 'Configuración guardada', message: 'Aplica desde el próximo día y en las próximas decisiones.' });
    } catch (error) {
      notify({
        tone: 'danger',
        title: 'No se guardó la configuración',
        message: error instanceof Error ? error.message : 'Inténtalo de nuevo en unos segundos.',
      });
    } finally {
      setSaving(false);
    }
  };

  const ownerOptions = [
    ...draft.owners.map((o) => ({ value: o, label: o })),
    { value: NO_AREA, label: 'Gerencia (sin área)' },
  ];

  return (
    <div className="arena-band page arena-stack arena-stack--section">
      <ArenaPageHead title="Configuración" subtitle="Qué vigila Centinela, a quién avisa y hasta dónde actúa" />
      {allowed ? null : (
        <p className="text-muted">Solo Analista o Gerencia cambian la configuración; aquí la consultas sin modificarla.</p>
      )}
      <ArenaTabs value={tab} onChange={setTab}>
        <ArenaTab value="kpis" label="KPIs vigilados">
          <div className="arena-stack arena-stack--group">
            <p className="text-muted">Centinela compara cada KPI vigilado con sus umbrales al empezar cada día.</p>
            <ArenaTable label="KPIs vigilados" columns={COLUMNS}>
              {draft.metrics.map((m) => (
                <ArenaTableRow key={m.metric}>
                  <ArenaTableCell>
                    <span className="arena-stack kpi">
                      <span className="kpi__name">{m.name}</span>
                      <span className="text-muted">{m.description}</span>
                      <span className="text-muted">Regla: {m.rule}</span>
                    </span>
                  </ArenaTableCell>
                  <ArenaTableCell>
                    <ArenaSwitch
                      label={`Vigilar ${m.name.toLowerCase()}`}
                      state={m.watched}
                      disabled={!allowed}
                      onFuncOn={() => changeMetric(m.metric, { watched: true })}
                      onFuncOff={() => changeMetric(m.metric, { watched: false })}
                    />
                  </ArenaTableCell>
                  <ArenaTableCell>
                    <div className="arena-stack kpi">
                      {m.thresholds.map((t) =>
                        t.editable ? (
                          <ArenaInput
                            key={t.key}
                            type="number"
                            min="0"
                            label={t.label}
                            hint={t.rule}
                            value={values[valueKey(m.metric, t.key)] ?? ''}
                            disabled={!allowed || !m.watched}
                            error={allowed && m.watched ? thresholdError(values[valueKey(m.metric, t.key)] ?? '') : undefined}
                            onChange={(value) => setValues({ ...values, [valueKey(m.metric, t.key)]: value })}
                          />
                        ) : (
                          <span key={t.key} className="text-muted">
                            {t.label}: {t.rule}
                          </span>
                        ),
                      )}
                      <span className="text-muted">Fuente: {m.source}</span>
                    </div>
                  </ArenaTableCell>
                </ArenaTableRow>
              ))}
            </ArenaTable>
          </div>
        </ArenaTab>
        <ArenaTab value="owners" label="Responsables">
          <div className="arena-stack arena-stack--group">
            <p className="text-muted">
              Qué área decide las alertas de cada KPI. Gerencia decide cualquier alerta, y sola las de un KPI sin área.
            </p>
            <div className="owners">
              {draft.metrics.map((m) => (
                <ArenaSelect
                  key={m.metric}
                  label={m.name}
                  options={ownerOptions}
                  value={m.owner ?? NO_AREA}
                  disabled={!allowed}
                  onChange={(value) => changeMetric(m.metric, { owner: value === NO_AREA ? null : value })}
                />
              ))}
            </div>
          </div>
        </ArenaTab>
        <ArenaTab value="autonomy" label="Autonomía">
          <div className="arena-stack arena-stack--group">
            <p className="text-muted">
              Durante el piloto ninguna acción se ejecuta sola: lo más que hace Centinela es preparar la acción y esperar tu
              aprobación.
            </p>
            <div className="autonomy">
              {ACTION_TYPES.map(({ type, name }) => (
                <section key={type} className="arena-stack arena-stack--group" aria-labelledby={`autonomy-${type}`}>
                  <h2 id={`autonomy-${type}`} className="autonomy__title">
                    {name}
                  </h2>
                  <ArenaRadioGroup
                    ariaLabel={`Autonomía para ${name.toLowerCase()}`}
                    value={draft.autonomy[type]}
                    disabled={!allowed}
                    onChange={(value) => changeAutonomy(type, value as AutonomyLevel)}
                  >
                    <ArenaRadio value="inform" label="Informa" hint="Muestra la acción propuesta sin que se apruebe desde Centinela" />
                    <ArenaRadio value="propose" label="Propone" hint="Prepara la acción y espera tu aprobación" />
                    <ArenaRadio value="execute" label="Ejecuta" hint="Se habilita en producción, con historial" disabled />
                  </ArenaRadioGroup>
                </section>
              ))}
            </div>
          </div>
        </ArenaTab>
      </ArenaTabs>
      {allowed ? (
        <div>
          <ArenaButton icon="ph-bold ph-floppy-disk" loading={saving} disabled={invalid} onClick={() => void save()}>
            Guardar cambios
          </ArenaButton>
        </div>
      ) : null}
    </div>
  );
}
