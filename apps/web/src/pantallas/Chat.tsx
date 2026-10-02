import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import {
  ArenaAlert,
  ArenaButton,
  ArenaSheet,
  ArenaSpinner,
  ArenaTag,
  ArenaTextarea,
  useArenaViewportBelow,
} from '@dravensoft/arena-react';
import { chat, consulta, obtenerAlerta } from '../api/client';
import type { Consulta, MensajeChat } from '../api/types';
import { FraseConCifras } from '../comun/FraseConCifras';
import { GraficoSerie, tituloDeFuente } from '../comun/GraficoSerie';
import { useSimulacion } from '../estado/Simulacion';

const ID_CAMPO = 'chat-pregunta';

type Entrada =
  | { id: number; rol: 'usuario'; texto: string }
  | { id: number; rol: 'centinela'; estado: 'buscando' | 'escribiendo'; paso: string; texto: string }
  | { id: number; rol: 'centinela'; estado: 'listo'; mensaje: MensajeChat }
  | { id: number; rol: 'centinela'; estado: 'error' };

const SUGERENCIAS_ALERTA: Record<string, string[]> = {
  'alerta-hogar': ['¿Qué clientes compran esos SKU?'],
};

const SUGERENCIAS_GLOBALES = ['¿Cómo va el margen de Hogar?', '¿Cuál es la tasa de cambio del dólar hoy?'];

function GraficoMensaje({ mensaje }: { mensaje: MensajeChat }) {
  const [fuente, setFuente] = useState<Consulta | null>(null);
  const primera = mensaje.cifras[0];
  useEffect(() => {
    if (primera) {
      consulta(primera.consultaId).then(setFuente, () => setFuente(null));
    }
  }, [primera]);
  if (!mensaje.serie || !primera || !fuente) {
    return null;
  }
  return (
    <GraficoSerie
      titulo={tituloDeFuente(fuente.vista)}
      nombre={fuente.descripcion}
      serie={mensaje.serie}
      unidad={primera.unidad}
      alto={160}
    />
  );
}

function Respuesta({ entrada }: { entrada: Exclude<Entrada, { rol: 'usuario' }> }) {
  if (entrada.estado === 'error') {
    return (
      <ArenaAlert tone="danger" title="No pude responder">
        Intenta de nuevo en unos segundos.
      </ArenaAlert>
    );
  }
  if (entrada.estado !== 'listo') {
    return (
      <div className="arena-stack arena-stack--group" aria-busy="true">
        {entrada.texto ? <p>{entrada.texto}</p> : null}
        {entrada.estado === 'buscando' ? <ArenaSpinner size="sm" label={entrada.paso} /> : null}
      </div>
    );
  }
  const { mensaje } = entrada;
  if (!mensaje.evidenciaSuficiente) {
    return (
      <ArenaAlert tone="info" icon="ph-bold ph-question" title="Sin evidencia suficiente">
        <FraseConCifras texto={mensaje.texto} cifras={mensaje.cifras} />
      </ArenaAlert>
    );
  }
  return (
    <div className="arena-stack arena-stack--group">
      <p>
        <FraseConCifras texto={mensaje.texto} cifras={mensaje.cifras} />
      </p>
      <GraficoMensaje mensaje={mensaje} />
    </div>
  );
}

export function Chat() {
  const movil = useArenaViewportBelow('lg');
  const { chat: estado, cerrarChat, quitarContextoChat } = useSimulacion();
  const [entradas, setEntradas] = useState<Entrada[]>([]);
  const [pregunta, setPregunta] = useState('');
  const [respondiendo, setRespondiendo] = useState(false);
  const [plegado, setPlegado] = useState(false);
  const [tituloAlerta, setTituloAlerta] = useState<string | null>(null);
  const conversacion = useRef<HTMLOListElement>(null);
  const origen = useRef<HTMLElement | null>(null);
  const siguiente = useRef(0);

  useEffect(() => {
    setTituloAlerta(null);
    if (estado.alertaId) {
      obtenerAlerta(estado.alertaId).then(
        (a) => setTituloAlerta(a.titulo.texto),
        () => setTituloAlerta(null),
      );
    }
  }, [estado.alertaId]);

  useEffect(() => {
    if (estado.abierto) {
      origen.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setPlegado(false);
      const cuadro = requestAnimationFrame(() => document.getElementById(ID_CAMPO)?.focus());
      return () => cancelAnimationFrame(cuadro);
    }
    origen.current?.focus();
    origen.current = null;
    return undefined;
  }, [estado.abierto]);

  useEffect(() => {
    conversacion.current?.lastElementChild?.scrollIntoView({ block: 'end' });
  }, [entradas]);

  const actualizar = (id: number, cambio: (e: Entrada) => Entrada) =>
    setEntradas((actuales) => actuales.map((e) => (e.id === id ? cambio(e) : e)));

  const preguntar = async (texto: string) => {
    const limpia = texto.trim();
    if (!limpia || respondiendo) {
      return;
    }
    siguiente.current += 2;
    const idPregunta = siguiente.current - 1;
    const idRespuesta = siguiente.current;
    setPregunta('');
    setRespondiendo(true);
    setEntradas((actuales) => [
      ...actuales,
      { id: idPregunta, rol: 'usuario', texto: limpia },
      { id: idRespuesta, rol: 'centinela', estado: 'buscando', paso: 'Buscando la respuesta', texto: '' },
    ]);
    try {
      for await (const evento of chat({ pregunta: limpia, ...(estado.alertaId ? { alertaId: estado.alertaId } : {}) })) {
        if (evento.evento === 'paso') {
          const paso = evento.datos.descripcion;
          actualizar(idRespuesta, (e) => (e.rol === 'centinela' && e.estado === 'buscando' ? { ...e, paso } : e));
        } else if (evento.evento === 'fragmento') {
          const trozo = evento.datos.texto;
          actualizar(idRespuesta, (e) =>
            e.rol === 'centinela' && (e.estado === 'buscando' || e.estado === 'escribiendo')
              ? { ...e, estado: 'escribiendo', texto: e.texto + trozo }
              : e,
          );
        } else {
          const mensaje = evento.datos;
          actualizar(idRespuesta, () => ({ id: idRespuesta, rol: 'centinela', estado: 'listo', mensaje }));
        }
      }
    } catch {
      actualizar(idRespuesta, () => ({ id: idRespuesta, rol: 'centinela', estado: 'error' }));
    } finally {
      setRespondiendo(false);
    }
  };

  const enviar = (evento: FormEvent) => {
    evento.preventDefault();
    void preguntar(pregunta);
  };

  const teclas = (evento: KeyboardEvent<HTMLFormElement>) => {
    if (evento.key === 'Enter' && !evento.shiftKey && evento.target instanceof HTMLTextAreaElement) {
      evento.preventDefault();
      void preguntar(pregunta);
    }
  };

  const sugerencias = estado.alertaId ? (SUGERENCIAS_ALERTA[estado.alertaId] ?? []) : SUGERENCIAS_GLOBALES;

  return (
    <ArenaSheet
      open={estado.abierto}
      placement={movil ? 'bottom' : 'end'}
      title="Preguntar a Centinela"
      collapsed={plegado}
      onCollapsedChange={setPlegado}
      dismissible
      onClose={cerrarChat}
      footer={
        <form className="arena-stack arena-stack--group chat__pie" onSubmit={enviar} onKeyDown={teclas}>
          <ArenaTextarea
            id={ID_CAMPO}
            label="Tu pregunta"
            rows={2}
            hint="Enter envía; Mayús + Enter, nueva línea"
            value={pregunta}
            onChange={setPregunta}
          />
          <div className="arena-row chat__enviar">
            <ArenaButton type="submit" variant="secondary" icon="ph-bold ph-paper-plane-right" loading={respondiendo} disabled={!pregunta.trim()}>
              Preguntar
            </ArenaButton>
          </div>
        </form>
      }
    >
      <div className="arena-stack arena-stack--group chat">
        <div className="chat__contexto">
          {estado.alertaId ? (
            <ArenaTag removable onRemove={quitarContextoChat}>
              Sobre: {tituloAlerta ?? 'esta alerta'}
            </ArenaTag>
          ) : (
            <p className="texto-tenue">Pregunta sobre cualquier indicador vigilado.</p>
          )}
        </div>
        {entradas.length === 0 ? (
          <div className="arena-stack arena-stack--group">
            <p className="texto-tenue">Respondo con los datos de la empresa, y cada cifra lleva su fuente. Por ejemplo:</p>
            <div className="arena-stack chat__sugerencias">
              {sugerencias.map((s) => (
                <ArenaButton key={s} variant="ghost" size="sm" icon="ph-bold ph-chat-circle-text" onClick={() => void preguntar(s)}>
                  {s}
                </ArenaButton>
              ))}
            </div>
          </div>
        ) : null}
        <ol ref={conversacion} className="chat__conversacion" role="log" aria-label="Conversación">
          {entradas.map((e) => (
            <li key={e.id} className={e.rol === 'usuario' ? 'burbuja burbuja--usuario' : 'burbuja burbuja--centinela'}>
              <span className="rotulo">{e.rol === 'usuario' ? 'Tú' : 'Centinela'}</span>
              {e.rol === 'usuario' ? <p>{e.texto}</p> : <Respuesta entrada={e} />}
            </li>
          ))}
        </ol>
      </div>
    </ArenaSheet>
  );
}
