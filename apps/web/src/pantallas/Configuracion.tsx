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
import { configuracion, ErrorApi, guardarConfiguracion } from '../api/client';
import type { Configuracion as DatosConfiguracion, MetricaVigilada, NivelAutonomia, TipoAccion } from '../api/types';
import { useSimulacion } from '../estado/Simulacion';

const TIPOS_ACCION: { tipo: TipoAccion; nombre: string }[] = [
  { tipo: 'borrador_correo', nombre: 'Borrador de correo' },
  { tipo: 'tarea', nombre: 'Tarea' },
  { tipo: 'borrador_orden_compra', nombre: 'Borrador de orden de compra' },
  { tipo: 'borrador_ajuste_precio', nombre: 'Borrador de ajuste de precio' },
];

const COLUMNAS: ArenaTableColumn[] = [{ header: 'KPI' }, { header: 'Vigilar' }, { header: 'Umbral' }];

type Umbrales = Record<string, string>;

function errorUmbral(texto: string): string | undefined {
  if (texto.trim() === '') {
    return 'Escribe un número';
  }
  return Number(texto) < 0 ? 'El umbral no puede ser negativo' : undefined;
}

export function Configuracion() {
  const { avisar } = useSimulacion();
  const [pestana, setPestana] = useState('kpis');
  const [borrador, setBorrador] = useState<DatosConfiguracion | null>(null);
  const [umbrales, setUmbrales] = useState<Umbrales>({});
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    configuracion().then((datos) => {
      setBorrador(datos);
      setUmbrales(Object.fromEntries(datos.metricas.map((m) => [m.metrica, String(m.umbral.valor)])));
    });
  }, []);

  if (!borrador) {
    return (
      <div className="arena-band pagina arena-stack arena-stack--section">
        <ArenaPageHead title="Configuración" />
        <ArenaSkeleton variant="text" lines={8} />
      </div>
    );
  }

  const cambiarMetrica = (metrica: MetricaVigilada['metrica'], cambio: Partial<MetricaVigilada>) =>
    setBorrador({ ...borrador, metricas: borrador.metricas.map((m) => (m.metrica === metrica ? { ...m, ...cambio } : m)) });

  const cambiarAutonomia = (tipo: TipoAccion, nivel: NivelAutonomia) =>
    setBorrador({ ...borrador, autonomia: { ...borrador.autonomia, [tipo]: nivel } });

  const invalido = borrador.metricas.some((m) => m.vigilada && errorUmbral(umbrales[m.metrica] ?? '') !== undefined);

  const guardar = async () => {
    setGuardando(true);
    try {
      const nueva: DatosConfiguracion = {
        ...borrador,
        metricas: borrador.metricas.map((m) => ({ ...m, umbral: { ...m.umbral, valor: Number(umbrales[m.metrica]) } })),
      };
      setBorrador(await guardarConfiguracion(nueva));
      avisar({ tone: 'success', title: 'Configuración guardada', message: 'Aplica desde la próxima revisión de los indicadores.' });
    } catch (error) {
      avisar({
        tone: 'danger',
        title: 'No se guardó la configuración',
        message: error instanceof ErrorApi ? error.message : 'Inténtalo de nuevo en unos segundos.',
      });
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="arena-band pagina arena-stack arena-stack--section">
      <ArenaPageHead title="Configuración" subtitle="Qué vigila Centinela, a quién avisa y hasta dónde actúa" />
      <ArenaTabs value={pestana} onChange={setPestana}>
        <ArenaTab value="kpis" label="KPIs vigilados">
          <div className="arena-stack arena-stack--group">
            <p className="texto-tenue">Centinela compara cada KPI vigilado con su umbral al empezar cada día.</p>
            <ArenaTable label="KPIs vigilados" columns={COLUMNAS}>
              {borrador.metricas.map((m) => (
                <ArenaTableRow key={m.metrica}>
                  <ArenaTableCell>
                    <span className="arena-stack kpi">
                      <span className="kpi__nombre">{m.nombre}</span>
                      <span className="texto-tenue">{m.descripcion}</span>
                    </span>
                  </ArenaTableCell>
                  <ArenaTableCell>
                    <ArenaSwitch
                      label={`Vigilar ${m.nombre.toLowerCase()}`}
                      state={m.vigilada}
                      onFuncOn={() => cambiarMetrica(m.metrica, { vigilada: true })}
                      onFuncOff={() => cambiarMetrica(m.metrica, { vigilada: false })}
                    />
                  </ArenaTableCell>
                  <ArenaTableCell>
                    <ArenaInput
                      type="number"
                      min="0"
                      label={m.umbral.etiqueta}
                      hint={`Regla: ${m.regla}`}
                      value={umbrales[m.metrica] ?? ''}
                      disabled={!m.vigilada}
                      error={m.vigilada ? errorUmbral(umbrales[m.metrica] ?? '') : undefined}
                      onChange={(valor) => setUmbrales({ ...umbrales, [m.metrica]: valor })}
                    />
                  </ArenaTableCell>
                </ArenaTableRow>
              ))}
            </ArenaTable>
          </div>
        </ArenaTab>
        <ArenaTab value="responsables" label="Responsables">
          <div className="arena-stack arena-stack--group">
            <p className="texto-tenue">Quién recibe cada alerta para decidirla.</p>
            <div className="responsables">
              {borrador.metricas.map((m) => (
                <ArenaSelect
                  key={m.metrica}
                  label={m.nombre}
                  options={borrador.responsables.map((r) => ({ value: r, label: r }))}
                  value={m.responsable}
                  onChange={(valor) => cambiarMetrica(m.metrica, { responsable: valor })}
                />
              ))}
            </div>
          </div>
        </ArenaTab>
        <ArenaTab value="autonomia" label="Autonomía">
          <div className="arena-stack arena-stack--group">
            <p className="texto-tenue">
              Durante el piloto ninguna acción se ejecuta sola: lo más que hace Centinela es preparar la acción y esperar tu
              aprobación.
            </p>
            <div className="autonomia">
              {TIPOS_ACCION.map(({ tipo, nombre }) => (
                <section key={tipo} className="arena-stack arena-stack--group" aria-labelledby={`autonomia-${tipo}`}>
                  <h2 id={`autonomia-${tipo}`} className="autonomia__titulo">
                    {nombre}
                  </h2>
                  <ArenaRadioGroup
                    ariaLabel={`Autonomía para ${nombre.toLowerCase()}`}
                    value={borrador.autonomia[tipo]}
                    onChange={(valor) => cambiarAutonomia(tipo, valor as NivelAutonomia)}
                  >
                    <ArenaRadio value="informa" label="Informa" hint="Avisa del hallazgo sin proponer acciones" />
                    <ArenaRadio value="propone" label="Propone" hint="Prepara la acción y espera tu aprobación" />
                    <ArenaRadio value="ejecuta" label="Ejecuta" hint="Se habilita en producción, con historial" disabled />
                  </ArenaRadioGroup>
                </section>
              ))}
            </div>
          </div>
        </ArenaTab>
      </ArenaTabs>
      <div>
        <ArenaButton icon="ph-bold ph-floppy-disk" loading={guardando} disabled={invalido} onClick={() => void guardar()}>
          Guardar cambios
        </ArenaButton>
      </div>
    </div>
  );
}
