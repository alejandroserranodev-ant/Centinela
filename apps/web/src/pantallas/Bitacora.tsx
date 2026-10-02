import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArenaPageHead,
  ArenaSelect,
  ArenaSkeleton,
  ArenaTable,
  ArenaTableCell,
  ArenaTableRow,
  ArenaTag,
  type ArenaTableColumn,
} from '@dravensoft/arena-react';
import { bitacora, listarAlertas } from '../api/client';
import type { Actor, Agente, Alerta, EventoBitacora, TipoEventoBitacora } from '../api/types';
import { useSimulacion } from '../estado/Simulacion';
import { fechaCorta, fechaHoraCorta } from '../formato';

const POR_PAGINA = 10;

const EVENTO: Record<TipoEventoBitacora, string> = {
  alerta: 'Detección',
  evidencia: 'Evidencia',
  propuesta: 'Propuesta',
  decision: 'Decisión',
  accion: 'Acción',
  resultado: 'Resultado',
};

const ETAPA: Record<Agente, string> = {
  vigia: 'detección',
  analista: 'análisis',
  estratega: 'propuesta',
  ejecutor: 'ejecución',
};

const COLUMNAS: ArenaTableColumn[] = [
  { header: 'Registrado', width: 'calc(var(--sp-1) * 32)' },
  { header: 'Día simulado', mono: true, width: 'calc(var(--sp-1) * 28)' },
  { header: 'Alerta' },
  { header: 'Evento' },
  { header: 'Quién' },
  { header: 'Detalle' },
  { header: 'Fuente', mobileLayout: 'block', width: 'calc(var(--sp-1) * 40)' },
];

function quien(actor: Actor): string {
  return actor.tipo === 'agente' ? `Centinela · ${ETAPA[actor.agente]}` : `${actor.nombre} (${actor.rol})`;
}

function BotonFuente({ consultaId, abrir }: { consultaId: string; abrir: (id: string) => void }) {
  return (
    <button type="button" className="enlace" onClick={() => abrir(consultaId)}>
      Ver de dónde sale
    </button>
  );
}

export function Bitacora() {
  const navigate = useNavigate();
  const { version, abrirConsulta } = useSimulacion();
  const [alertaId, setAlertaId] = useState('');
  const [tipo, setTipo] = useState<TipoEventoBitacora | ''>('');
  const [pagina, setPagina] = useState(1);
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [eventos, setEventos] = useState<EventoBitacora[] | null>(null);

  useEffect(() => {
    listarAlertas().then(setAlertas);
  }, [version]);

  useEffect(() => {
    bitacora({ ...(alertaId ? { alertaId } : {}), ...(tipo ? { tipo } : {}) }).then(setEventos);
  }, [alertaId, tipo, version]);

  const titulos = new Map(alertas.map((a) => [a.id, a.titulo.texto]));
  const visibles = eventos?.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA) ?? [];

  return (
    <div className="arena-band pagina arena-stack arena-stack--section">
      <ArenaPageHead title="Bitácora" subtitle="Cada detección, propuesta, decisión y resultado, del más reciente al más antiguo" />
      <div className="filtros">
        <ArenaSelect
          label="Alerta"
          options={[{ value: '', label: 'Todas las alertas' }, ...alertas.map((a) => ({ value: a.id, label: a.titulo.texto }))]}
          value={alertaId}
          onChange={(valor) => {
            setAlertaId(valor);
            setPagina(1);
          }}
        />
        <ArenaSelect
          label="Tipo de evento"
          options={[
            { value: '', label: 'Todos los eventos' },
            ...Object.entries(EVENTO).map(([valor, etiqueta]) => ({ value: valor, label: etiqueta })),
          ]}
          value={tipo}
          onChange={(valor) => {
            setTipo(valor as TipoEventoBitacora | '');
            setPagina(1);
          }}
        />
      </div>
      {eventos === null ? (
        <ArenaSkeleton variant="text" lines={10} />
      ) : (
        <ArenaTable
          label="Eventos de la bitácora"
          columns={COLUMNAS}
          page={{ index: pagina, size: POR_PAGINA, total: eventos.length }}
          onPageChange={setPagina}
          empty="Ningún evento coincide con estos filtros."
        >
          {visibles.map((e) => (
            <ArenaTableRow key={e.id}>
              <ArenaTableCell>{fechaHoraCorta(e.fecha)}</ArenaTableCell>
              <ArenaTableCell>{fechaCorta(e.diaSimulado)}</ArenaTableCell>
              <ArenaTableCell href={`/alertas/${e.alertaId}`} onNavigate={() => navigate(`/alertas/${e.alertaId}`)}>
                {titulos.get(e.alertaId) ?? e.alertaId}
              </ArenaTableCell>
              <ArenaTableCell>
                <ArenaTag>{EVENTO[e.tipo]}</ArenaTag>
              </ArenaTableCell>
              <ArenaTableCell>{quien(e.actor)}</ArenaTableCell>
              <ArenaTableCell>{e.detalle}</ArenaTableCell>
              <ArenaTableCell>
                {e.consultaId ? <BotonFuente consultaId={e.consultaId} abrir={abrirConsulta} /> : <span className="texto-tenue">Sin cifras</span>}
              </ArenaTableCell>
            </ArenaTableRow>
          ))}
        </ArenaTable>
      )}
    </div>
  );
}
