import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ArenaSpinner } from '@dravensoft/arena-react';
import { getSession, login } from '../api/client';
import { getToken, onUnauthorized, setToken } from '../api/session';
import type { Persona } from '../api/types';

interface Session {
  persona: Persona | null;
  token: string | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [token, setCurrentToken] = useState<string | null>(() => getToken());
  const [persona, setPersona] = useState<Persona | null>(null);
  const [ready, setReady] = useState(() => getToken() === null);

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
    getSession()
      .then(setPersona)
      .catch(signOut)
      .finally(() => setReady(true));
  }, [signOut]);

  const signIn = useCallback(async (email: string, password: string) => {
    const session = await login(email, password);
    setToken(session.token);
    setCurrentToken(session.token);
    setPersona(session.persona);
    setReady(true);
  }, []);

  const value = useMemo<Session>(
    () => ({ persona, token, ready, signIn, signOut }),
    [persona, token, ready, signIn, signOut],
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
  const { persona, ready } = useSession();
  const location = useLocation();
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
