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
import { listarAlertas, resumenBandeja } from '../api/client';
import type { Alerta, Cifra, ResumenBandeja } from '../api/types';
import { useSimulacion } from '../estado/Simulacion';
import { fecha, numero, pesos, pesosCompactos } from '../formato';
import { Detalle } from './Detalle';
import { ListaAlertas } from './ListaAlertas';

type Filtro = 'pendientes' | 'decididas' | 'todas';

const FILTROS = [
  { value: 'pendientes', label: 'Por decidir' },
  { value: 'decididas', label: 'Decididas' },
  { value: 'todas', label: 'Todas' },
];

const DECIDIDAS: Alerta['estado'][] = ['aprobada', 'rechazada', 'ejecutada'];

function pasaFiltro(alerta: Alerta, filtro: Filtro): boolean {
  const decidida = DECIDIDAS.includes(alerta.estado);
  return filtro === 'todas' || (filtro === 'decididas' ? decidida : !decidida);
}

function Total({ etiqueta, valor, sub, cifra }: { etiqueta: string; valor: string; sub: string; cifra: Cifra }) {
  const { abrirConsulta } = useSimulacion();
  return (
    <div className="arena-stack arena-stack--group total">
      <ArenaStatCard label={etiqueta} value={valor} sub={sub} />
      <button type="button" className="enlace" onClick={() => abrirConsulta(cifra.consultaId)}>
        Ver de dónde sale<span className="arena-sr-only"> {etiqueta.toLowerCase()}</span>
      </button>
    </div>
  );
}

function TotalesCompactos({ resumen }: { resumen: ResumenBandeja }) {
  const { abrirConsulta } = useSimulacion();
  const totales = [
    { etiqueta: 'En riesgo hoy', valor: pesosCompactos(resumen.dineroEnRiesgo.valor), cifra: resumen.dineroEnRiesgo },
    { etiqueta: 'Por decidir', valor: numero(resumen.decisionesPendientes.valor), cifra: resumen.decisionesPendientes },
    { etiqueta: 'Recuperable al mes', valor: pesosCompactos(resumen.recuperableMes.valor), cifra: resumen.recuperableMes },
  ];
  return (
    <dl className="totales-compactos">
      {totales.map((t) => (
        <div key={t.etiqueta}>
          <dt className="rotulo">{t.etiqueta}</dt>
          <dd>
            <button type="button" className="cifra" onClick={() => abrirConsulta(t.cifra.consultaId)}>
              {t.valor}
              <span className="arena-sr-only">, ver de dónde sale</span>
            </button>
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function Bandeja() {
  const { id } = useParams();
  const movil = useArenaViewportBelow('lg');
  const angosto = useArenaViewportBelow('sm');
  const { diaSimulado, version, avanzar, avanzando } = useSimulacion();
  const [filtro, setFiltro] = useState<Filtro>('pendientes');
  const [alertas, setAlertas] = useState<Alerta[] | null>(null);
  const [resumen, setResumen] = useState<ResumenBandeja | null>(null);

  useEffect(() => {
    listarAlertas().then(setAlertas);
    resumenBandeja().then(setResumen);
  }, [version]);

  if (movil && id) {
    return (
      <div className="arena-band pagina">
        <Detalle id={id} />
      </div>
    );
  }

  const visibles = alertas?.filter((a) => pasaFiltro(a, filtro)) ?? null;

  return (
    <div className="arena-band pagina arena-stack arena-stack--section">
      <ArenaPageHead
        title="Bandeja de decisiones"
        subtitle={diaSimulado ? `Situación al ${fecha(diaSimulado)}` : undefined}
      />
      {resumen && angosto ? (
        <TotalesCompactos resumen={resumen} />
      ) : resumen ? (
        <div className="totales">
          <Total
            etiqueta="En riesgo hoy"
            valor={pesos(resumen.dineroEnRiesgo.valor)}
            sub="en las alertas por decidir"
            cifra={resumen.dineroEnRiesgo}
          />
          <Total
            etiqueta="Por decidir"
            valor={numero(resumen.decisionesPendientes.valor)}
            sub={resumen.decisionesPendientes.valor === 1 ? 'decisión espera tu aprobación' : 'decisiones esperan tu aprobación'}
            cifra={resumen.decisionesPendientes}
          />
          <Total
            etiqueta="Recuperable al mes"
            valor={pesos(resumen.recuperableMes.valor)}
            sub="si apruebas lo propuesto"
            cifra={resumen.recuperableMes}
          />
        </div>
      ) : (
        <ArenaSkeleton variant="block" height="calc(var(--sp-1) * 28)" />
      )}
      <div className={movil ? 'bandeja' : 'bandeja bandeja--lectura'}>
        <section className="arena-stack bandeja__lista" aria-label="Alertas">
          <ArenaSegmentedControl
            ariaLabel="Estado de las alertas"
            size="sm"
            options={FILTROS}
            value={filtro}
            onChange={(valor) => setFiltro(valor as Filtro)}
          />
          {visibles === null ? (
            <ArenaSkeleton variant="text" lines={6} />
          ) : visibles.length === 0 ? (
            <ArenaEmptyState
              icon="ph-bold ph-check-circle"
              headingLevel="h2"
              title={filtro === 'decididas' ? 'Aún no hay decisiones tomadas' : 'No hay decisiones pendientes'}
              message={
                filtro === 'decididas'
                  ? 'Lo que apruebes o rechaces queda aquí y en la bitácora.'
                  : 'Todos los indicadores vigilados están dentro de sus umbrales. Avanza el día para revisar el siguiente.'
              }
              action={
                filtro === 'decididas' ? undefined : (
                  <ArenaButton variant="secondary" icon="ph-bold ph-fast-forward" loading={avanzando} onClick={avanzar}>
                    Avanzar un día
                  </ArenaButton>
                )
              }
            />
          ) : (
            <ListaAlertas alertas={visibles} seleccionada={id} />
          )}
        </section>
        {movil ? null : (
          <section className="bandeja__columna" aria-label="Detalle de la alerta">
            {id ? (
              <Detalle id={id} />
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
