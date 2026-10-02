import type { Cifra, UnidadCifra } from './api/types';

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
const formatoFechaCorta = new Intl.DateTimeFormat('es-CO', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'America/Bogota',
});
const formatoMes = new Intl.DateTimeFormat('es-CO', { month: 'long', year: 'numeric', timeZone: 'America/Bogota' });
const formatoEjeMes = new Intl.DateTimeFormat('es-CO', { month: 'short', timeZone: 'America/Bogota' });
const formatoEjeDia = new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'short', timeZone: 'America/Bogota' });
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

export function fechaCorta(dia: string): string {
  return formatoFechaCorta
    .formatToParts(new Date(`${dia}T12:00:00-05:00`))
    .filter((parte) => parte.type !== 'literal')
    .map((parte) => parte.value.replace(/\.$/, ''))
    .join(' ');
}

export function mes(dia: string): string {
  return formatoMes.format(new Date(`${dia}T12:00:00-05:00`));
}

export function ejeMes(dia: string): string {
  return formatoEjeMes.format(new Date(`${dia}T12:00:00-05:00`));
}

export function ejeDia(dia: string): string {
  return formatoEjeDia.format(new Date(`${dia}T12:00:00-05:00`));
}

export function fechaHora(iso: string): string {
  return formatoFechaHora.format(new Date(iso));
}

export function enUnidad(valor: number, unidad: UnidadCifra): string {
  switch (unidad) {
    case 'COP':
      return pesos(valor);
    case 'porcentaje':
      return porcentaje(valor);
    case 'puntos':
      return puntos(valor);
    case 'dias':
      return dias(valor);
    case 'unidades':
      return unidades(valor);
  }
}

export function cifra(c: Cifra): string {
  return enUnidad(c.valor, c.unidad);
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
