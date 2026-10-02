import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { arenaToastDelay, type ArenaToastEntry, type ArenaToastNotice, type ArenaToastQueue } from '@dravensoft/arena-react';
import { avanzarDia, estadoSimulacion } from '../api/client';
import type { PasoAgente, Usuario } from '../api/types';
import { fecha } from '../formato';

export interface AccionAviso {
  etiqueta: string;
  ejecutar: () => void;
}

interface EstadoChat {
  abierto: boolean;
  alertaId?: string;
}

interface Simulacion {
  diaSimulado: string | null;
  usuario: Usuario | null;
  version: number;
  avanzando: boolean;
  paso: PasoAgente | null;
  avanzar: () => Promise<void>;
  cambio: () => void;
  avisos: ArenaToastQueue;
  avisar: (aviso: ArenaToastNotice, accion?: AccionAviso) => void;
  accionDeAviso: (id: number) => AccionAviso | undefined;
  consultaAbierta: string | null;
  abrirConsulta: (id: string) => void;
  cerrarConsulta: () => void;
  chat: EstadoChat;
  abrirChat: (alertaId?: string) => void;
  cerrarChat: () => void;
  quitarContextoChat: () => void;
}

const Contexto = createContext<Simulacion | null>(null);

const DURACION_AVISO = { default: 5000, actionable: 5000 };

function useAvisos(): ArenaToastQueue {
  const [toasts, setToasts] = useState<ArenaToastEntry[]>([]);
  const siguiente = useRef(0);
  const relojes = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    clearTimeout(relojes.current.get(id));
    relojes.current.delete(id);
    setToasts((actuales) => actuales.filter((t) => t.id !== id));
  }, []);

  const raise = useCallback(
    (aviso: ArenaToastNotice) => {
      siguiente.current += 1;
      const id = siguiente.current;
      setToasts((actuales) => [...actuales, { ...aviso, id }]);
      const espera = arenaToastDelay(aviso, DURACION_AVISO);
      if (espera !== null) {
        relojes.current.set(id, setTimeout(() => dismiss(id), espera));
      }
      return id;
    },
    [dismiss],
  );

  const clear = useCallback(() => {
    relojes.current.forEach(clearTimeout);
    relojes.current.clear();
    setToasts([]);
  }, []);

  return useMemo(() => ({ toasts, raise, dismiss, clear }), [toasts, raise, dismiss, clear]);
}

export function SimulacionProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const avisos = useAvisos();
  const acciones = useRef(new Map<number, AccionAviso>());
  const [diaSimulado, setDiaSimulado] = useState<string | null>(null);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [version, setVersion] = useState(0);
  const [avanzando, setAvanzando] = useState(false);
  const [paso, setPaso] = useState<PasoAgente | null>(null);
  const [consultaAbierta, setConsultaAbierta] = useState<string | null>(null);
  const [chat, setChat] = useState<EstadoChat>({ abierto: false });

  useEffect(() => {
    estadoSimulacion().then((estado) => {
      setDiaSimulado(estado.diaSimulado);
      setUsuario(estado.usuario);
    });
  }, []);

  const cambio = useCallback(() => setVersion((v) => v + 1), []);

  const { raise } = avisos;
  const avisar = useCallback(
    (aviso: ArenaToastNotice, accion?: AccionAviso) => {
      const id = raise({ dismissible: true, ...aviso, ...(accion ? { actionLabel: accion.etiqueta } : {}) });
      if (accion) {
        acciones.current.set(id, accion);
      }
    },
    [raise],
  );

  const accionDeAviso = useCallback((id: number) => acciones.current.get(id), []);

  const avanzar = useCallback(async () => {
    if (avanzando) {
      return;
    }
    setAvanzando(true);
    try {
      for await (const evento of avanzarDia()) {
        if (evento.evento === 'paso') {
          setPaso(evento.datos);
        } else if (evento.evento === 'alerta') {
          cambio();
        } else {
          setDiaSimulado(evento.datos.diaSimulado);
          cambio();
          const nuevas = evento.datos.alertasNuevas;
          if (nuevas.length === 0) {
            avisar({
              tone: 'neutral',
              title: `Sin hallazgos el ${fecha(evento.datos.diaSimulado)}`,
              message: 'Todos los indicadores están dentro de sus umbrales.',
            });
          } else {
            avisar(
              {
                tone: 'gold',
                title:
                  nuevas.length === 1
                    ? `Una decisión nueva el ${fecha(evento.datos.diaSimulado)}`
                    : `${nuevas.length} decisiones nuevas el ${fecha(evento.datos.diaSimulado)}`,
              },
              { etiqueta: 'Ver', ejecutar: () => navigate(`/alertas/${nuevas[0]}`) },
            );
          }
        }
      }
    } catch {
      avisar({ tone: 'danger', title: 'No se pudo avanzar el día', message: 'Inténtalo de nuevo en unos segundos.' });
    } finally {
      setPaso(null);
      setAvanzando(false);
    }
  }, [avanzando, avisar, cambio, navigate]);

  const valor = useMemo<Simulacion>(
    () => ({
      diaSimulado,
      usuario,
      version,
      avanzando,
      paso,
      avanzar,
      cambio,
      avisos,
      avisar,
      accionDeAviso,
      consultaAbierta,
      abrirConsulta: setConsultaAbierta,
      cerrarConsulta: () => setConsultaAbierta(null),
      chat,
      abrirChat: (alertaId?: string) => setChat({ abierto: true, ...(alertaId ? { alertaId } : {}) }),
      cerrarChat: () => setChat({ abierto: false }),
      quitarContextoChat: () => setChat((c) => ({ abierto: c.abierto })),
    }),
    [diaSimulado, usuario, version, avanzando, paso, avanzar, cambio, avisos, avisar, accionDeAviso, consultaAbierta, chat],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSimulacion(): Simulacion {
  const valor = useContext(Contexto);
  if (!valor) {
    throw new Error('useSimulacion necesita un SimulacionProvider');
  }
  return valor;
}
