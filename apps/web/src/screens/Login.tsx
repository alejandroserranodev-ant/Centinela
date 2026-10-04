import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ArenaAlert, ArenaButton, ArenaInput, ArenaUnauthCard } from '@dravensoft/arena-react';
import { ApiError } from '../api/client';
import { useSession } from '../state/Session';

function returnPath(state: unknown): string {
  const from = (state as { from?: unknown } | null)?.from;
  return typeof from === 'string' && from.startsWith('/') && !from.startsWith('/ingresar') ? from : '/';
}

export function Login() {
  const { persona, signIn } = useSession();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const target = returnPath(location.state);

  if (persona && !sending) {
    return <Navigate to={target} replace />;
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim() || !password) {
      setError('Escribe tu correo y tu contraseña para ingresar.');
      return;
    }
    setSending(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
      navigate(target, { replace: true });
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? e.message : 'No se pudo ingresar. Inténtalo de nuevo en unos segundos.');
      setSending(false);
    }
  };

  return (
    <main className="login">
      <ArenaUnauthCard
        eyebrow="Centinela"
        title="Ingresar"
        headingLevel="h1"
        footer="Distribuidora Andina S.A.S. · acceso del equipo"
      >
        <form className="arena-stack arena-stack--group" onSubmit={submit} noValidate>
          {error ? (
            <ArenaAlert tone="danger" title="No pudiste ingresar">
              {error}
            </ArenaAlert>
          ) : null}
          <ArenaInput
            label="Correo"
            type="email"
            name="email"
            autoComplete="username"
            required
            value={email}
            onChange={setEmail}
          />
          <ArenaInput
            label="Contraseña"
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={setPassword}
          />
          <ArenaButton type="submit" variant="primary" icon="ph-bold ph-sign-in" full loading={sending}>
            Ingresar
          </ArenaButton>
        </form>
      </ArenaUnauthCard>
    </main>
  );
}
