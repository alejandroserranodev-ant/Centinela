import { useEffect, useState } from 'react';
import {
  ArenaButton,
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
import { useSimulation } from '../state/Simulation';

const ACTION_TYPES: { type: ActionType; name: string }[] = [
  { type: 'email_draft', name: 'Borrador de correo' },
  { type: 'task', name: 'Tarea' },
  { type: 'purchase_order_draft', name: 'Borrador de orden de compra' },
  { type: 'price_change_draft', name: 'Borrador de ajuste de precio' },
];

const COLUMNS: ArenaTableColumn[] = [{ header: 'KPI' }, { header: 'Vigilar' }, { header: 'Umbral' }];

type Thresholds = Record<string, string>;

function thresholdError(text: string): string | undefined {
  if (text.trim() === '') {
    return 'Escribe un número';
  }
  return Number(text) < 0 ? 'El umbral no puede ser negativo' : undefined;
}

export function Settings() {
  const { notify } = useSimulation();
  const [tab, setTab] = useState('kpis');
  const [draft, setDraft] = useState<SettingsData | null>(null);
  const [thresholds, setThresholds] = useState<Thresholds>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getSettings().then((data) => {
      setDraft(data);
      setThresholds(Object.fromEntries(data.metrics.map((m) => [m.metric, String(m.threshold.value)])));
    });
  }, []);

  if (!draft) {
    return (
      <div className="arena-band page arena-stack arena-stack--section">
        <ArenaPageHead title="Configuración" />
        <ArenaSkeleton variant="text" lines={8} />
      </div>
    );
  }

  const changeMetric = (metric: WatchedMetric['metric'], change: Partial<WatchedMetric>) =>
    setDraft({ ...draft, metrics: draft.metrics.map((m) => (m.metric === metric ? { ...m, ...change } : m)) });

  const changeAutonomy = (type: ActionType, level: AutonomyLevel) =>
    setDraft({ ...draft, autonomy: { ...draft.autonomy, [type]: level } });

  const invalid = draft.metrics.some((m) => m.watched && thresholdError(thresholds[m.metric] ?? '') !== undefined);

  const save = async () => {
    setSaving(true);
    try {
      const next: SettingsData = {
        ...draft,
        metrics: draft.metrics.map((m) => ({ ...m, threshold: { ...m.threshold, value: Number(thresholds[m.metric]) } })),
      };
      setDraft(await saveSettings(next));
      notify({ tone: 'success', title: 'Configuración guardada', message: 'Aplica desde la próxima revisión de los indicadores.' });
    } catch (error) {
      notify({
        tone: 'danger',
        title: 'No se guardó la configuración',
        message: error instanceof ApiError ? error.message : 'Inténtalo de nuevo en unos segundos.',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="arena-band page arena-stack arena-stack--section">
      <ArenaPageHead title="Configuración" subtitle="Qué vigila Centinela, a quién avisa y hasta dónde actúa" />
      <ArenaTabs value={tab} onChange={setTab}>
        <ArenaTab value="kpis" label="KPIs vigilados">
          <div className="arena-stack arena-stack--group">
            <p className="text-muted">Centinela compara cada KPI vigilado con su umbral al empezar cada día.</p>
            <ArenaTable label="KPIs vigilados" columns={COLUMNS}>
              {draft.metrics.map((m) => (
                <ArenaTableRow key={m.metric}>
                  <ArenaTableCell>
                    <span className="arena-stack kpi">
                      <span className="kpi__name">{m.name}</span>
                      <span className="text-muted">{m.description}</span>
                    </span>
                  </ArenaTableCell>
                  <ArenaTableCell>
                    <ArenaSwitch
                      label={`Vigilar ${m.name.toLowerCase()}`}
                      state={m.watched}
                      onFuncOn={() => changeMetric(m.metric, { watched: true })}
                      onFuncOff={() => changeMetric(m.metric, { watched: false })}
                    />
                  </ArenaTableCell>
                  <ArenaTableCell>
                    <ArenaInput
                      type="number"
                      min="0"
                      label={m.threshold.label}
                      hint={`Regla: ${m.rule}`}
                      value={thresholds[m.metric] ?? ''}
                      disabled={!m.watched}
                      error={m.watched ? thresholdError(thresholds[m.metric] ?? '') : undefined}
                      onChange={(value) => setThresholds({ ...thresholds, [m.metric]: value })}
                    />
                  </ArenaTableCell>
                </ArenaTableRow>
              ))}
            </ArenaTable>
          </div>
        </ArenaTab>
        <ArenaTab value="owners" label="Responsables">
          <div className="arena-stack arena-stack--group">
            <p className="text-muted">Quién recibe cada alerta para decidirla.</p>
            <div className="owners">
              {draft.metrics.map((m) => (
                <ArenaSelect
                  key={m.metric}
                  label={m.name}
                  options={draft.owners.map((o) => ({ value: o, label: o }))}
                  value={m.owner}
                  onChange={(value) => changeMetric(m.metric, { owner: value })}
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
                    onChange={(value) => changeAutonomy(type, value as AutonomyLevel)}
                  >
                    <ArenaRadio value="inform" label="Informa" hint="Avisa del hallazgo sin proponer acciones" />
                    <ArenaRadio value="propose" label="Propone" hint="Prepara la acción y espera tu aprobación" />
                    <ArenaRadio value="execute" label="Ejecuta" hint="Se habilita en producción, con historial" disabled />
                  </ArenaRadioGroup>
                </section>
              ))}
            </div>
          </div>
        </ArenaTab>
      </ArenaTabs>
      <div>
        <ArenaButton icon="ph-bold ph-floppy-disk" loading={saving} disabled={invalid} onClick={() => void save()}>
          Guardar cambios
        </ArenaButton>
      </div>
    </div>
  );
}
