import { Route, Routes } from 'react-router-dom';
import { SimulationProvider } from './state/Simulation';
import { Bitacora } from './screens/Bitacora';
import { Inbox } from './screens/Inbox';
import { Settings } from './screens/Settings';
import { Shell } from './shell/Shell';

export function App() {
  return (
    <SimulationProvider>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<Inbox />} />
          <Route path="alertas/:id" element={<Inbox />} />
          <Route path="bitacora" element={<Bitacora />} />
          <Route path="configuracion" element={<Settings />} />
          <Route path="*" element={<Inbox />} />
        </Route>
      </Routes>
    </SimulationProvider>
  );
}
