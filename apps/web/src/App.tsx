import { Route, Routes } from 'react-router-dom';
import { SimulacionProvider } from './estado/Simulacion';
import { Bandeja } from './pantallas/Bandeja';
import { Bitacora } from './pantallas/Bitacora';
import { Configuracion } from './pantallas/Configuracion';
import { Shell } from './shell/Shell';

export function App() {
  return (
    <SimulacionProvider>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<Bandeja />} />
          <Route path="alertas/:id" element={<Bandeja />} />
          <Route path="bitacora" element={<Bitacora />} />
          <Route path="configuracion" element={<Configuracion />} />
          <Route path="*" element={<Bandeja />} />
        </Route>
      </Routes>
    </SimulacionProvider>
  );
}
