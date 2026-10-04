import {
  ArenaAppBar,
  ArenaBottomNav,
  ArenaBottomNavItem,
  ArenaIconButton,
  ArenaMain,
  ArenaSideNav,
  ArenaSideNavItem,
  ArenaSkipLink,
  ArenaToast,
  ArenaToastHost,
  useArenaTheme,
  useArenaViewportBelow,
} from '@dravensoft/arena-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useSession } from '../state/Session';
import { useSimulation } from '../state/Simulation';
import { roleLabel } from '../roles';
import { QueryDialog } from '../common/QueryDialog';
import { Chat } from '../screens/Chat';
import { Clock } from './Clock';
import { CurrentStep } from './CurrentStep';

const DESTINATIONS = [
  { id: 'inbox', label: 'Bandeja', icon: 'ph-bold ph-tray', path: '/' },
  { id: 'bitacora', label: 'Bitácora', icon: 'ph-bold ph-scroll', path: '/bitacora' },
  { id: 'settings', label: 'Configuración', icon: 'ph-bold ph-sliders-horizontal', path: '/configuracion' },
];

function activeDestination(path: string): string {
  if (path.startsWith('/bitacora')) {
    return 'bitacora';
  }
  if (path.startsWith('/configuracion')) {
    return 'settings';
  }
  return 'inbox';
}

export function Shell() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const mobile = useArenaViewportBelow('lg');
  const [theme, setTheme] = useArenaTheme();
  const { toasts, toastAction, openChat, chat } = useSimulation();
  const { persona, signOut } = useSession();
  const active = activeDestination(pathname);
  const go = (id: string) => {
    const destination = DESTINATIONS.find((d) => d.id === id);
    if (destination) {
      navigate(destination.path);
    } else if (id === 'ask') {
      openChat();
    }
  };

  return (
    <div className={['arena-shell shell', mobile ? 'shell--mobile' : '', !mobile && chat.open ? 'shell--chat' : ''].filter(Boolean).join(' ')}>
      <ArenaSkipLink label="Saltar al contenido" />
      <ArenaAppBar
        brand={
          <Link to="/" className="brand">
            Centinela
          </Link>
        }
        actions={
          <div className="bar__actions">
            <Clock />
            {mobile ? null : (
              <ArenaIconButton
                icon="ph-bold ph-chat-circle-text"
                label="Preguntar"
                showLabel
                pressed={chat.open}
                onClick={() => openChat()}
              />
            )}
            <ArenaIconButton
              icon="ph-bold ph-moon"
              label="Tema oscuro"
              size={mobile ? 'sm' : 'md'}
              pressed={theme === 'dark'}
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            />
            {persona && !mobile ? (
              <div className="person">
                <span className="person__name">{persona.name}</span>
                <span className="text-muted">{roleLabel(persona)}</span>
              </div>
            ) : null}
            <ArenaIconButton
              icon="ph-bold ph-sign-out"
              label="Salir"
              showLabel={!mobile}
              size={mobile ? 'sm' : 'md'}
              onClick={signOut}
            />
          </div>
        }
      />
      <CurrentStep />
      <div className="arena-shell__main shell__body">
        {mobile ? null : (
          <div className="shell__rail">
            <ArenaSideNav ariaLabel="Secciones" active={active} onNav={go}>
              {DESTINATIONS.map((d) => (
                <ArenaSideNavItem key={d.id} id={d.id} label={d.label} icon={d.icon} href={d.path} />
              ))}
            </ArenaSideNav>
          </div>
        )}
        <ArenaMain>
          <Outlet />
        </ArenaMain>
      </div>
      {mobile ? (
        <ArenaBottomNav ariaLabel="Secciones" active={chat.open ? 'ask' : active} onNav={go}>
          {[
            ...DESTINATIONS.map((d) => <ArenaBottomNavItem key={d.id} id={d.id} label={d.label} icon={d.icon} href={d.path} />),
            <ArenaBottomNavItem key="ask" id="ask" label="Preguntar" icon="ph-bold ph-chat-circle-text" />,
          ]}
        </ArenaBottomNav>
      ) : null}
      <ArenaToastHost placement={mobile ? 'top-end' : 'bottom-end'}>
        {toasts.toasts.map((t) => (
          <ArenaToast
            key={t.id}
            title={t.title}
            message={t.message}
            tone={t.tone}
            actionLabel={t.actionLabel}
            onAction={() => {
              toastAction(t.id)?.run();
              toasts.dismiss(t.id);
            }}
            persist={t.persist}
            dismissible
            onClose={() => toasts.dismiss(t.id)}
          />
        ))}
      </ArenaToastHost>
      <Chat />
      <QueryDialog />
    </div>
  );
}
