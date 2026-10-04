import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ArenaErrorState, ArenaSpinner } from '@dravensoft/arena-react';
import { ApiError, getSession, login } from '../api/client';
import { getToken, onUnauthorized, setToken } from '../api/session';
import type { Persona } from '../api/types';

interface Session {
  persona: Persona | null;
  token: string | null;
  ready: boolean;
  unreachable: boolean;
  retry: () => void;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [token, setCurrentToken] = useState<string | null>(() => getToken());
  const [persona, setPersona] = useState<Persona | null>(null);
  const [ready, setReady] = useState(() => getToken() === null);
  const [unreachable, setUnreachable] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const signOut = useCallback(() => {
    setToken(null);
    setCurrentToken(null);
    setPersona(null);
    setReady(true);
  }, []);

  useEffect(() => {
    onUnauthorized(signOut);
    return () => onUnauthorized(null);
  }, [signOut]);

  useEffect(() => {
    if (getToken() === null) {
      return;
    }
    setUnreachable(false);
    getSession()
      .then((current) => {
        setPersona(current);
        setReady(true);
      })
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) {
          signOut();
        } else {
          setUnreachable(true);
        }
      });
  }, [signOut, attempt]);

  const retry = useCallback(() => setAttempt((a) => a + 1), []);

  const signIn = useCallback(async (email: string, password: string) => {
    const session = await login(email, password);
    setToken(session.token);
    setCurrentToken(session.token);
    setPersona(session.persona);
    setUnreachable(false);
    setReady(true);
  }, []);

  const value = useMemo<Session>(
    () => ({ persona, token, ready, unreachable, retry, signIn, signOut }),
    [persona, token, ready, unreachable, retry, signIn, signOut],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error('useSession needs a SessionProvider');
  }
  return value;
}

export function RequireSession({ children }: { children: ReactNode }) {
  const { persona, ready, unreachable, retry } = useSession();
  const location = useLocation();
  if (unreachable) {
    return (
      <div className="session-wait">
        <ArenaErrorState
          title="No se pudo comprobar tu sesión"
          message="La API no responde. Tu sesión sigue guardada: vuelve a intentarlo cuando esté en marcha."
          retryLabel="Reintentar"
          onRetry={retry}
        />
      </div>
    );
  }
  if (!ready) {
    return (
      <div className="session-wait">
        <ArenaSpinner label="Comprobando la sesión" />
      </div>
    );
  }
  if (!persona) {
    return <Navigate to="/ingresar" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return <>{children}</>;
}
