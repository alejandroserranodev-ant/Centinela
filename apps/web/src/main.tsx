import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ArenaLocaleProvider, initArenaTheme } from '@dravensoft/arena-react';
import './icons.generated.css';
import './arena.generated.css';
import './app.css';
import { App } from './App';

const PALABRAS = {
  locale: 'es-CO',
  paginationPrevious: 'Anterior',
  paginationNext: 'Siguiente',
  tableSortBy: 'Ordenar por',
  tableEmpty: 'No hay datos.',
  toastClose: 'Cerrar',
  toastPinned: 'Fijado',
  toastPinnedHint: 'No se cierra solo',
  sheetClose: 'Cerrar',
  alertDismiss: 'Descartar',
  tagRemove: 'Quitar',
  skeletonLabel: 'Cargando',
  spinnerLabel: 'Cargando',
  errorStateTitle: 'Algo salió mal',
  lineChartName: '{label}, gráfico de líneas',
  chartTablePoint: 'Fecha',
  chartTableSeries: 'Serie',
};

initArenaTheme({
  palettes: [
    { name: 'light', polarity: 'light' },
    { name: 'dark', polarity: 'dark' },
  ],
  default: 'light',
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ArenaLocaleProvider value={PALABRAS}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ArenaLocaleProvider>
  </StrictMode>,
);
