import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArenaAlert,
  ArenaButton,
  ArenaErrorState,
  ArenaSection,
  ArenaSkeleton,
  ArenaSpinner,
  useArenaViewportBelow,
} from '@dravensoft/arena-react';
import { consulta, obtenerAlerta } from '../api/client';
import type { Alerta, Consulta, Evidencia } from '../api/types';
import { Confianza, Estado, Severidad } from '../comun/Etiquetas';
import { CifraEnlazada, FraseConCifras } from '../comun/FraseConCifras';
import { GraficoSerie, tituloDeFuente } from '../comun/GraficoSerie';
import { useSimulacion } from '../estado/Simulacion';
import { fecha } from '../formato';
import { AccionesPropuestas } from './AccionesPropuestas';
import { ComoLlegue } from './ComoLlegue';

function Prueba({ evidencia }: { evidencia: Evidencia }) {
  const [fuente, setFuente] = useState<Consulta | null>(null);
  useEffect(() => {
    consulta(evidencia.consultaId).then(setFuente, () => setFuente(null));
  }, [evidencia.consultaId]);
  const unidad = evidencia.afirmacion.cifras[0]?.unidad ?? 'unidades';
  return (
    <li className="arena-stack arena-stack--group">
      <p>
        <FraseConCifras texto={evidencia.afirmacion.texto} cifras={evidencia.afirmacion.cifras} />
      </p>
      {evidencia.serie && fuente ? (
        <GraficoSerie titulo={tituloDeFuente(fuente.vista)} nombre={fuente.descripcion} serie={evidencia.serie} unidad={unidad} />
      ) : null}
    </li>
  );
}

function Resultado({ alerta }: { alerta: Alerta }) {
  if (alerta.estado === 'rechazada') {
    return (
      <ArenaAlert tone="info" title="Rechazaste esta propuesta">
        El motivo está en la bitácora. La alerta no vuelve a la bandeja de pendientes.
      </ArenaAlert>
    );
  }
  if (alerta.estado === 'aprobada' || alerta.estado === 'ejecutada') {
    const accion = alerta.acciones.find((a) => a.id === alerta.accionEjecutada?.accionId);
    return (
      <ArenaAlert tone="success" title={accion ? `Aprobada: ${accion.titulo}` : 'Aprobada'}>
        {alerta.accionEjecutada?.resultado ?? 'La acción está en curso.'}
      </ArenaAlert>
    );
  }
  return null;
}

export function Detalle({ id }: { id: string }) {
  const navigate = useNavigate();
  const movil = useArenaViewportBelow('lg');
  const { version, abrirChat } = useSimulacion();
  const [alerta, setAlerta] = useState<Alerta | null>(null);
  const [falla, setFalla] = useState(false);

  useEffect(() => {
    setFalla(false);
    obtenerAlerta(id).then(setAlerta, () => setFalla(true));
  }, [id, version]);

  useEffect(() => {
    setAlerta(null);
  }, [id]);

  const volver = movil ? (
    <div>
      <ArenaButton variant="ghost" size="sm" icon="ph-bold ph-arrow-left" onClick={() => navigate('/')}>
        Volver a la bandeja
      </ArenaButton>
    </div>
  ) : null;

  if (falla) {
    return (
      <div className="arena-stack">
        {volver}
        <ArenaErrorState
          icon="ph-bold ph-magnifying-glass"
          title="No encontramos esta alerta"
          message="Puede que el enlace sea de otro día simulado. Vuelve a la bandeja para ver las alertas vigentes."
          retryLabel="Volver a la bandeja"
          onRetry={() => navigate('/')}
        />
      </div>
    );
  }

  if (!alerta || alerta.id !== id) {
    return <ArenaSkeleton variant="text" lines={8} />;
  }

  const pendiente = alerta.estado === 'propuesta';
  const enAnalisis = alerta.estado === 'nueva' || alerta.estado === 'en_analisis';

  return (
    <article className="arena-stack arena-stack--section detalle" aria-labelledby="titulo-alerta">
      {volver}
      <header className="arena-stack arena-stack--group">
        <div className="arena-row detalle__etiquetas">
          <Severidad nivel={alerta.severidad} />
          <Estado estado={alerta.estado} />
          <Confianza nivel={alerta.confianza.nivel} />
          <time className="texto-tenue" dateTime={alerta.fechaSimulada}>
            Detectada el {fecha(alerta.fechaSimulada)}
          </time>
        </div>
        <h2 id="titulo-alerta" className="detalle__titulo">
          <FraseConCifras texto={alerta.titulo.texto} cifras={alerta.titulo.cifras} />
        </h2>
        <p className="detalle__dinero">
          <span>
            <span className="rotulo">En riesgo</span> <CifraEnlazada cifra={alerta.pesosEnRiesgo} />
          </span>
          {alerta.recuperableMes ? (
            <span>
              <span className="rotulo">Recuperable</span> <CifraEnlazada cifra={alerta.recuperableMes} /> al mes
            </span>
          ) : null}
        </p>
        <div>
          <ArenaButton variant="ghost" size="sm" icon="ph-bold ph-chat-circle-text" onClick={() => abrirChat(alerta.id)}>
            Preguntar sobre esta alerta
          </ArenaButton>
        </div>
      </header>

      <Resultado alerta={alerta} />

      {enAnalisis ? (
        <div className="arena-row en-analisis">
          <ArenaSpinner size="sm" label="Analizando la alerta" />
          <p>Estamos buscando la causa y preparando la propuesta. Aparece aquí en unos segundos.</p>
        </div>
      ) : (
        <>

      <ArenaSection title="Qué pasó" headingLevel="h3">
        {alerta.causa.tipo === 'identificada' ? (
          <div className="arena-stack arena-stack--group">
            <p className="detalle__causa">
              <FraseConCifras texto={alerta.causa.frase.texto} cifras={alerta.causa.frase.cifras} />
            </p>
            {alerta.confianza.supuestos.length > 0 ? (
              <p className="texto-tenue">Supone que {alerta.confianza.supuestos.map((s) => s.charAt(0).toLowerCase() + s.slice(1)).join('; ')}.</p>
            ) : null}
          </div>
        ) : (
          <ArenaAlert tone="warning" icon="ph-bold ph-question" title="No encontramos evidencia suficiente para explicar la causa">
            {alerta.causa.motivo} Preferimos decirlo antes que adivinar: las consultas revisadas están en "Cómo llegué aquí".
          </ArenaAlert>
        )}
      </ArenaSection>

      {alerta.causa.tipo === 'identificada' ? (
        <ArenaSection title="Evidencia" headingLevel="h3">
          <ul className="arena-stack evidencias">
            {alerta.causa.evidencia.map((e) => (
              <Prueba key={e.consultaId + e.afirmacion.texto} evidencia={e} />
            ))}
          </ul>
        </ArenaSection>
      ) : null}

      {pendiente ? (
        <ArenaSection
          title="Acciones propuestas"
          headingLevel="h3"
          description={alerta.acciones.length > 1 ? 'Elige una, revísala y apruébala, edítala o rechaza la propuesta.' : undefined}
        >
          <AccionesPropuestas key={alerta.id} alerta={alerta} />
        </ArenaSection>
      ) : null}

      <ComoLlegue alerta={alerta} />
        </>
      )}
    </article>
  );
}
