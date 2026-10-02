import type { ReactNode } from 'react';
import type { Cifra } from '../api/types';
import { useSimulacion } from '../estado/Simulacion';
import { cifra as formatoCifra, cifraEnTexto } from '../formato';

interface Tramo {
  inicio: number;
  fin: number;
  cifra: Cifra;
}

function ubicar(texto: string, cifras: Cifra[]): Tramo[] {
  const tramos: Tramo[] = [];
  for (const cifra of cifras) {
    const buscado = cifraEnTexto(cifra);
    let desde = 0;
    while (desde <= texto.length) {
      const inicio = texto.indexOf(buscado, desde);
      if (inicio < 0) {
        break;
      }
      const fin = inicio + buscado.length;
      if (!tramos.some((t) => inicio < t.fin && fin > t.inicio)) {
        tramos.push({ inicio, fin, cifra });
        break;
      }
      desde = inicio + 1;
    }
  }
  return tramos.sort((a, b) => a.inicio - b.inicio);
}

export function FraseConCifras({ texto, cifras }: { texto: string; cifras: Cifra[] }) {
  const { abrirConsulta } = useSimulacion();
  const partes: ReactNode[] = [];
  let cursor = 0;
  for (const tramo of ubicar(texto, cifras)) {
    partes.push(texto.slice(cursor, tramo.inicio));
    partes.push(
      <button
        key={tramo.inicio}
        type="button"
        className="cifra"
        title="Ver de dónde sale esta cifra"
        onClick={() => abrirConsulta(tramo.cifra.consultaId)}
      >
        {texto.slice(tramo.inicio, tramo.fin)}
        <span className="arena-sr-only">, ver de dónde sale</span>
      </button>,
    );
    cursor = tramo.fin;
  }
  partes.push(texto.slice(cursor));
  return <>{partes}</>;
}

export function CifraEnlazada({ cifra }: { cifra: Cifra }) {
  const { abrirConsulta } = useSimulacion();
  return (
    <button type="button" className="cifra" title="Ver de dónde sale esta cifra" onClick={() => abrirConsulta(cifra.consultaId)}>
      {formatoCifra(cifra)}
      <span className="arena-sr-only">, ver de dónde sale</span>
    </button>
  );
}
