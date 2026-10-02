import { useState } from 'react';
import { ArenaButton, ArenaCard, ArenaKeyValue, ArenaRadio, ArenaRadioGroup } from '@dravensoft/arena-react';
import { decidir, ErrorApi } from '../api/client';
import type { Accion, Alerta, Decision, TipoAccion } from '../api/types';
import { Confianza } from '../comun/Etiquetas';
import { CifraEnlazada, FraseConCifras } from '../comun/FraseConCifras';
import { useSimulacion } from '../estado/Simulacion';
import { cifra } from '../formato';
import { DialogoEditar } from './DialogoEditar';
import { DialogoRechazo } from './DialogoRechazo';
import { nombreParametro } from './parametros';

const TIPO: Record<TipoAccion, string> = {
  borrador_correo: 'Borrador de correo',
  tarea: 'Tarea',
  borrador_orden_compra: 'Borrador de orden de compra',
  borrador_ajuste_precio: 'Borrador de ajuste de precio',
};

const NIVEL: Record<Accion['confianza']['nivel'], string> = { alta: 'alta', media: 'media', baja: 'baja' };

function resumenAccion(accion: Accion): string {
  const impacto = accion.impacto
    ? `${cifra(accion.impacto.cifra)} ${accion.impacto.periodo === 'mes' ? 'al mes' : 'una vez'}`
    : 'Sin impacto en pesos estimado';
  return `${TIPO[accion.tipo]} · ${impacto} · confianza ${NIVEL[accion.confianza.nivel]}`;
}

export function AccionesPropuestas({ alerta }: { alerta: Alerta }) {
  const { avisar, cambio } = useSimulacion();
  const [elegidaId, setElegidaId] = useState(alerta.acciones[0].id);
  const [aprobando, setAprobando] = useState(false);
  const [editando, setEditando] = useState(false);
  const [rechazando, setRechazando] = useState(false);
  const elegida = alerta.acciones.find((a) => a.id === elegidaId) ?? alerta.acciones[0];

  const enviar = async (decision: Decision) => {
    try {
      const resultado = await decidir(alerta.id, decision);
      if (decision.tipo === 'rechazar') {
        avisar({ tone: 'neutral', title: 'Propuesta rechazada', message: 'El motivo quedó en la bitácora.' });
      } else {
        avisar({
          tone: 'success',
          title: `Aprobada: ${elegida.titulo}`,
          message: resultado.accionEjecutada?.resultado,
        });
      }
      setEditando(false);
      setRechazando(false);
      cambio();
    } catch (e) {
      if (e instanceof ErrorApi && e.estado === 409) {
        avisar({ tone: 'danger', title: 'Esta alerta ya se decidió', message: 'Recargamos su estado actual.' });
        setEditando(false);
        setRechazando(false);
        cambio();
        return;
      }
      throw e;
    }
  };

  const aprobar = async () => {
    setAprobando(true);
    try {
      await enviar({ tipo: 'aprobar', accionId: elegida.id });
    } catch {
      avisar({ tone: 'danger', title: 'No se pudo aprobar', message: 'Inténtalo de nuevo en unos segundos.' });
    } finally {
      setAprobando(false);
    }
  };

  return (
    <div className="arena-stack">
      {alerta.acciones.length > 1 ? (
        <ArenaRadioGroup ariaLabel="Acción a aprobar" value={elegida.id} onChange={setElegidaId}>
          {alerta.acciones.map((accion) => (
            <ArenaRadio key={accion.id} value={accion.id} label={accion.titulo} hint={resumenAccion(accion)} />
          ))}
        </ArenaRadioGroup>
      ) : null}
      <ArenaCard eyebrow={TIPO[elegida.tipo]} title={elegida.titulo} headingLevel="h4" action={<Confianza nivel={elegida.confianza.nivel} />}>
        <div className="arena-stack arena-stack--group">
          <p>
            <FraseConCifras texto={elegida.descripcion.texto} cifras={elegida.descripcion.cifras} />
          </p>
          <p>
            <span className="rotulo">Impacto estimado</span>{' '}
            {elegida.impacto ? (
              <>
                <CifraEnlazada cifra={elegida.impacto.cifra} /> {elegida.impacto.periodo === 'mes' ? 'al mes' : 'una sola vez'}
              </>
            ) : (
              'sin impacto en pesos estimado'
            )}
          </p>
          {elegida.confianza.supuestos.length > 0 ? (
            <div>
              <span className="rotulo">Supone que</span>
              <ul className="supuestos">
                {elegida.confianza.supuestos.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <ArenaKeyValue
            rows={Object.entries(elegida.parametros).map(([clave, valor]) => ({
              term: nombreParametro(clave),
              value: String(valor),
              numeric: typeof valor === 'number',
            }))}
          />
        </div>
      </ArenaCard>
      <div className="arena-row arena-row--component decision">
        <ArenaButton variant="primary" icon="ph-bold ph-check" loading={aprobando} onClick={aprobar}>
          Aprobar
        </ArenaButton>
        <ArenaButton variant="secondary" icon="ph-bold ph-pencil-simple" onClick={() => setEditando(true)}>
          Editar
        </ArenaButton>
        <ArenaButton variant="danger" icon="ph-bold ph-x" onClick={() => setRechazando(true)}>
          Rechazar
        </ArenaButton>
      </div>
      <p className="texto-tenue">
        Aprobar deja un borrador o una tarea: nada se envía ni se publica hasta que una persona lo haga.
      </p>
      <DialogoEditar
        accion={elegida}
        abierto={editando}
        onCerrar={() => setEditando(false)}
        onAprobar={(parametros) => enviar({ tipo: 'editar', accionId: elegida.id, parametros })}
      />
      <DialogoRechazo
        abierto={rechazando}
        onCerrar={() => setRechazando(false)}
        onRechazar={(motivo) => enviar({ tipo: 'rechazar', motivo })}
      />
    </div>
  );
}
