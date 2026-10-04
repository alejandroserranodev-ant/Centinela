import { Route, Routes } from 'react-router-dom';
import { RequireSession, SessionProvider } from './state/Session';
import { SimulationProvider } from './state/Simulation';
import { Bitacora } from './screens/Bitacora';
import { Inbox } from './screens/Inbox';
import { Login } from './screens/Login';
import { Settings } from './screens/Settings';
import { Shell } from './shell/Shell';

export function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route path="ingresar" element={<Login />} />
        <Route
          element={
            <RequireSession>
              <SimulationProvider>
                <Shell />
              </SimulationProvider>
            </RequireSession>
          }
        >
          <Route index element={<Inbox />} />
          <Route path="alertas/:id" element={<Inbox />} />
          <Route path="bitacora" element={<Bitacora />} />
          <Route path="configuracion" element={<Settings />} />
          <Route path="*" element={<Inbox />} />
        </Route>
      </Routes>
    </SessionProvider>
  );
}
