import { ArenaMain, ArenaPageHead } from '@dravensoft/arena-react';

export function App() {
  return (
    <div className="arena-shell">
      <div className="arena-shell__main">
        <ArenaMain>
          <div className="arena-band page-block">
            <ArenaPageHead title="Bandeja de decisiones" subtitle="Maqueta en construcción" />
          </div>
        </ArenaMain>
      </div>
    </div>
  );
}
