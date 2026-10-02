import type { Cifra } from './api/types';

const formatoPesos = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
const formatoPesosCompactos = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  notation: 'compact',
  maximumFractionDigits: 1,
});
const formatoNumero = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 1 });
const formatoPorcentaje = new Intl.NumberFormat('es-CO', { style: 'percent', maximumFractionDigits: 1 });
const formatoFecha = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long', timeZone: 'America/Bogota' });
const formatoFechaHora = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'long',
  timeStyle: 'short',
  timeZone: 'America/Bogota',
});

export function pesos(valor: number): string {
  return formatoPesos.format(valor);
}

export function pesosCompactos(valor: number): string {
  return formatoPesosCompactos.format(valor);
}

export function numero(valor: number): string {
  return formatoNumero.format(valor);
}

export function porcentaje(valor: number): string {
  return formatoPorcentaje.format(valor / 100);
}

export function puntos(valor: number): string {
  return `${numero(valor)} ${Math.abs(valor) === 1 ? 'punto' : 'puntos'}`;
}

export function dias(valor: number): string {
  return `${numero(valor)} ${Math.abs(valor) === 1 ? 'día' : 'días'}`;
}

export function unidades(valor: number): string {
  return `${numero(valor)} ${Math.abs(valor) === 1 ? 'unidad' : 'unidades'}`;
}

export function fecha(dia: string): string {
  return formatoFecha.format(new Date(`${dia}T12:00:00-05:00`));
}

export function fechaHora(iso: string): string {
  return formatoFechaHora.format(new Date(iso));
}

export function cifra(c: Cifra): string {
  switch (c.unidad) {
    case 'COP':
      return pesos(c.valor);
    case 'porcentaje':
      return porcentaje(c.valor);
    case 'puntos':
      return puntos(c.valor);
    case 'dias':
      return dias(c.valor);
    case 'unidades':
      return unidades(c.valor);
  }
}

export function cifraEnTexto(c: Cifra): string {
  switch (c.unidad) {
    case 'COP':
      return pesosCompactos(c.valor);
    case 'porcentaje':
      return porcentaje(c.valor);
    default:
      return numero(c.valor);
  }
}
