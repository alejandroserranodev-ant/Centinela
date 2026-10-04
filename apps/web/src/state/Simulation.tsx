import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { arenaToastDelay, type ArenaToastEntry, type ArenaToastNotice, type ArenaToastQueue } from '@dravensoft/arena-react';
import { advanceDay, ApiError, getSimulatedDay } from '../api/client';
import type { AgentStep } from '../api/types';
import { formatDate } from '../format';

export interface ToastAction {
  label: string;
  run: () => void;
}

interface ChatState {
  open: boolean;
  alertId?: string;
}

interface Simulation {
  simulatedDay: string | null;
  version: number;
  advancing: boolean;
  step: AgentStep | null;
  advance: () => Promise<void>;
  changed: () => void;
  toasts: ArenaToastQueue;
  notify: (toast: ArenaToastNotice, action?: ToastAction) => void;
  toastAction: (id: number) => ToastAction | undefined;
  openQueryId: string | null;
  openQuery: (id: string) => void;
  closeQuery: () => void;
  chat: ChatState;
  openChat: (alertId?: string) => void;
  closeChat: () => void;
  clearChatContext: () => void;
}

const SimulationContext = createContext<Simulation | null>(null);

const TOAST_DURATION = { default: 5000, actionable: 5000 };

function useToasts(): ArenaToastQueue {
  const [toasts, setToasts] = useState<ArenaToastEntry[]>([]);
  const next = useRef(0);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const raise = useCallback(
    (toast: ArenaToastNotice) => {
      next.current += 1;
      const id = next.current;
      setToasts((current) => [...current, { ...toast, id }]);
      const delay = arenaToastDelay(toast, TOAST_DURATION);
      if (delay !== null) {
        timers.current.set(id, setTimeout(() => dismiss(id), delay));
      }
      return id;
    },
    [dismiss],
  );

  const clear = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current.clear();
    setToasts([]);
  }, []);

  return useMemo(() => ({ toasts, raise, dismiss, clear }), [toasts, raise, dismiss, clear]);
}

export function SimulationProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const toasts = useToasts();
  const actions = useRef(new Map<number, ToastAction>());
  const [simulatedDay, setSimulatedDay] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [advancing, setAdvancing] = useState(false);
  const [step, setStep] = useState<AgentStep | null>(null);
  const [openQueryId, setOpenQueryId] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatState>({ open: false });

  const changed = useCallback(() => setVersion((v) => v + 1), []);

  const { raise } = toasts;
  const notify = useCallback(
    (toast: ArenaToastNotice, action?: ToastAction) => {
      const id = raise({ dismissible: true, ...toast, ...(action ? { actionLabel: action.label } : {}) });
      if (action) {
        actions.current.set(id, action);
      }
    },
    [raise],
  );

  const toastAction = useCallback((id: number) => actions.current.get(id), []);

  useEffect(() => {
    getSimulatedDay()
      .then(setSimulatedDay)
      .catch((e: unknown) => {
        if (!(e instanceof ApiError && e.status === 401)) {
          notify({
            tone: 'danger',
            title: 'No se pudo leer el día simulado',
            message: e instanceof Error ? e.message : 'Revisa que la API esté en marcha y recarga la página.',
          });
        }
      });
  }, [notify]);

  const advance = useCallback(async () => {
    if (advancing) {
      return;
    }
    setAdvancing(true);
    try {
      for await (const event of advanceDay()) {
        if (event.event === 'step') {
          setStep(event.data);
        } else if (event.event === 'alert') {
          changed();
        } else {
          setSimulatedDay(event.data.simulatedDay);
          changed();
          const newAlerts = event.data.newAlerts;
          if (newAlerts.length === 0) {
            notify({
              tone: 'neutral',
              title: `Sin hallazgos el ${formatDate(event.data.simulatedDay)}`,
              message: 'Todos los indicadores están dentro de sus umbrales.',
            });
          } else {
            notify(
              {
                tone: 'gold',
                title:
                  newAlerts.length === 1
                    ? `Una decisión nueva el ${formatDate(event.data.simulatedDay)}`
                    : `${newAlerts.length} decisiones nuevas el ${formatDate(event.data.simulatedDay)}`,
              },
              { label: 'Ver', run: () => navigate(`/alertas/${newAlerts[0]}`) },
            );
          }
        }
      }
    } catch (e: unknown) {
      if (!(e instanceof ApiError && e.status === 401)) {
        notify({
          tone: 'danger',
          title: 'No se pudo avanzar el día',
          message: e instanceof Error ? e.message : 'Inténtalo de nuevo en unos segundos.',
        });
      }
    } finally {
      setStep(null);
      setAdvancing(false);
    }
  }, [advancing, notify, changed, navigate]);

  const value = useMemo<Simulation>(
    () => ({
      simulatedDay,
      version,
      advancing,
      step,
      advance,
      changed,
      toasts,
      notify,
      toastAction,
      openQueryId,
      openQuery: setOpenQueryId,
      closeQuery: () => setOpenQueryId(null),
      chat,
      openChat: (alertId?: string) => setChat({ open: true, ...(alertId ? { alertId } : {}) }),
      closeChat: () => setChat({ open: false }),
      clearChatContext: () => setChat((c) => ({ open: c.open })),
    }),
    [simulatedDay, version, advancing, step, advance, changed, toasts, notify, toastAction, openQueryId, chat],
  );

  return <SimulationContext.Provider value={value}>{children}</SimulationContext.Provider>;
}

export function useSimulation(): Simulation {
  const value = useContext(SimulationContext);
  if (!value) {
    throw new Error('useSimulation needs a SimulationProvider');
  }
  return value;
}
