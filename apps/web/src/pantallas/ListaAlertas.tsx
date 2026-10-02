import { useRef, type KeyboardEvent } from 'react';
import { Link } from 'react-router-dom';
import type { Alerta } from '../api/types';
import { Confianza, Estado, Severidad } from '../comun/Etiquetas';
import { fecha, pesos } from '../formato';

interface Props {
  alertas: Alerta[];
  seleccionada?: string;
}

export function ListaAlertas({ alertas, seleccionada }: Props) {
  const lista = useRef<HTMLUListElement>(null);
  const enfocable = alertas.some((a) => a.id === seleccionada) ? seleccionada : alertas[0]?.id;

  const moverFoco = (evento: KeyboardEvent<HTMLUListElement>) => {
    const filas = Array.from(lista.current?.querySelectorAll<HTMLAnchorElement>('a.fila') ?? []);
    const actual = filas.indexOf(document.activeElement as HTMLAnchorElement);
    const destino: Record<string, number> = {
      ArrowDown: Math.min(actual + 1, filas.length - 1),
      ArrowUp: Math.max(actual - 1, 0),
      Home: 0,
      End: filas.length - 1,
    };
    if (actual < 0 || !(evento.key in destino)) {
      return;
    }
    evento.preventDefault();
    filas.forEach((fila, i) => (fila.tabIndex = i === destino[evento.key] ? 0 : -1));
    filas[destino[evento.key]]?.focus();
  };

  return (
    <ul ref={lista} className="lista-alertas" aria-label="Alertas, de mayor a menor riesgo en pesos" onKeyDown={moverFoco}>
      {alertas.map((alerta) => (
        <li key={alerta.id}>
          <Link
            to={`/alertas/${alerta.id}`}
            className="fila"
            tabIndex={alerta.id === enfocable ? 0 : -1}
            aria-current={alerta.id === seleccionada ? 'page' : undefined}
          >
            <span className="arena-row fila__cabeza">
              <Severidad nivel={alerta.severidad} />
              {alerta.estado === 'propuesta' ? null : <Estado estado={alerta.estado} />}
              <time className="texto-tenue" dateTime={alerta.fechaSimulada}>
                {fecha(alerta.fechaSimulada)}
              </time>
            </span>
            <span className="fila__titulo">{alerta.titulo.texto}</span>
            <span className="fila__cifras">
              <span>
                <span className="rotulo">En riesgo</span> <span className="arena-num">{pesos(alerta.pesosEnRiesgo.valor)}</span>
              </span>
              {alerta.recuperableMes ? (
                <span>
                  <span className="rotulo">Recuperable</span>{' '}
                  <span className="arena-num">{pesos(alerta.recuperableMes.valor)}</span> al mes
                </span>
              ) : null}
              <Confianza nivel={alerta.confianza.nivel} />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
