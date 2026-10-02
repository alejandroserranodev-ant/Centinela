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
import { useSimulacion } from '../estado/Simulacion';
import { DialogoConsulta } from '../comun/DialogoConsulta';
import { Chat } from '../pantallas/Chat';
import { PasoEnCurso } from './PasoEnCurso';
import { Reloj } from './Reloj';

const DESTINOS = [
  { id: 'bandeja', etiqueta: 'Bandeja', icono: 'ph-bold ph-tray', ruta: '/' },
  { id: 'bitacora', etiqueta: 'Bitácora', icono: 'ph-bold ph-scroll', ruta: '/bitacora' },
  { id: 'configuracion', etiqueta: 'Configuración', icono: 'ph-bold ph-sliders-horizontal', ruta: '/configuracion' },
];

function destinoActivo(ruta: string): string {
  if (ruta.startsWith('/bitacora')) {
    return 'bitacora';
  }
  if (ruta.startsWith('/configuracion')) {
    return 'configuracion';
  }
  return 'bandeja';
}

export function Shell() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const movil = useArenaViewportBelow('lg');
  const [tema, fijarTema] = useArenaTheme();
  const { avisos, accionDeAviso, abrirChat, chat } = useSimulacion();
  const activo = destinoActivo(pathname);
  const ir = (id: string) => {
    const destino = DESTINOS.find((d) => d.id === id);
    if (destino) {
      navigate(destino.ruta);
    } else if (id === 'preguntar') {
      abrirChat();
    }
  };

  return (
    <div className={['arena-shell shell', movil ? 'shell--movil' : '', !movil && chat.abierto ? 'shell--chat' : ''].filter(Boolean).join(' ')}>
      <ArenaSkipLink label="Saltar al contenido" />
      <ArenaAppBar
        brand={
          <Link to="/" className="marca">
            Centinela
          </Link>
        }
        actions={
          <div className="barra__acciones">
            <Reloj />
            {movil ? null : (
              <ArenaIconButton
                icon="ph-bold ph-chat-circle-text"
                label="Preguntar"
                showLabel
                pressed={chat.abierto}
                onClick={() => abrirChat()}
              />
            )}
            <ArenaIconButton
              icon="ph-bold ph-moon"
              label="Tema oscuro"
              size={movil ? 'sm' : 'md'}
              pressed={tema === 'dark'}
              onClick={() => fijarTema(tema === 'dark' ? 'light' : 'dark')}
            />
          </div>
        }
      />
      <PasoEnCurso />
      <div className="arena-shell__main shell__cuerpo">
        {movil ? null : (
          <div className="shell__riel">
            <ArenaSideNav ariaLabel="Secciones" active={activo} onNav={ir}>
              {DESTINOS.map((d) => (
                <ArenaSideNavItem key={d.id} id={d.id} label={d.etiqueta} icon={d.icono} href={d.ruta} />
              ))}
            </ArenaSideNav>
          </div>
        )}
        <ArenaMain>
          <Outlet />
        </ArenaMain>
      </div>
      {movil ? (
        <ArenaBottomNav ariaLabel="Secciones" active={chat.abierto ? 'preguntar' : activo} onNav={ir}>
          {[
            ...DESTINOS.map((d) => (
              <ArenaBottomNavItem key={d.id} id={d.id} label={d.etiqueta} icon={d.icono} href={d.ruta} />
            )),
            <ArenaBottomNavItem key="preguntar" id="preguntar" label="Preguntar" icon="ph-bold ph-chat-circle-text" />,
          ]}
        </ArenaBottomNav>
      ) : null}
      <ArenaToastHost placement={movil ? 'top-end' : 'bottom-end'}>
        {avisos.toasts.map((t) => (
          <ArenaToast
            key={t.id}
            title={t.title}
            message={t.message}
            tone={t.tone}
            actionLabel={t.actionLabel}
            onAction={() => {
              accionDeAviso(t.id)?.ejecutar();
              avisos.dismiss(t.id);
            }}
            persist={t.persist}
            dismissible
            onClose={() => avisos.dismiss(t.id)}
          />
        ))}
      </ArenaToastHost>
      <Chat />
      <DialogoConsulta />
    </div>
  );
}
