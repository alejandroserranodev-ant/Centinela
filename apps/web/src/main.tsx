import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ArenaLocaleProvider, initArenaTheme } from '@dravensoft/arena-react';
import './icons.generated.css';
import './arena.generated.css';
import './app.css';
import { App } from './App';

initArenaTheme({
  palettes: [
    { name: 'light', polarity: 'light' },
    { name: 'dark', polarity: 'dark' },
  ],
  default: 'light',
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ArenaLocaleProvider value={{ locale: 'es-CO', paginationPrevious: 'Anterior', paginationNext: 'Siguiente' }}>
      <App />
    </ArenaLocaleProvider>
  </StrictMode>,
);
