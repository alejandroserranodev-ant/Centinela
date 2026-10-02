import type { Figure, FigureUnit } from './api/types';

const pesosFormat = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
const compactPesosFormat = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  notation: 'compact',
  maximumFractionDigits: 1,
});
const numberFormat = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 1 });
const percentFormat = new Intl.NumberFormat('es-CO', { style: 'percent', maximumFractionDigits: 1 });
const dateFormat = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long', timeZone: 'America/Bogota' });
const shortDateFormat = new Intl.DateTimeFormat('es-CO', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'America/Bogota',
});
const monthFormat = new Intl.DateTimeFormat('es-CO', { month: 'long', year: 'numeric', timeZone: 'America/Bogota' });
const monthAxisFormat = new Intl.DateTimeFormat('es-CO', { month: 'short', timeZone: 'America/Bogota' });
const dayAxisFormat = new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'short', timeZone: 'America/Bogota' });
const isoDayFormat = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota' });
const timeFormat = new Intl.DateTimeFormat('es-CO', { timeStyle: 'short', timeZone: 'America/Bogota' });

export function formatPesos(value: number): string {
  return pesosFormat.format(value);
}

export function formatCompactPesos(value: number): string {
  return compactPesosFormat.format(value);
}

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

export function formatPercent(value: number): string {
  return percentFormat.format(value / 100);
}

export function formatPoints(value: number): string {
  return `${formatNumber(value)} ${Math.abs(value) === 1 ? 'punto' : 'puntos'}`;
}

export function formatDays(value: number): string {
  return `${formatNumber(value)} ${Math.abs(value) === 1 ? 'día' : 'días'}`;
}

export function formatUnits(value: number): string {
  return `${formatNumber(value)} ${Math.abs(value) === 1 ? 'unidad' : 'unidades'}`;
}

export function formatDate(day: string): string {
  return dateFormat.format(new Date(`${day}T12:00:00-05:00`));
}

export function formatShortDate(day: string): string {
  return shortDateFormat
    .formatToParts(new Date(`${day}T12:00:00-05:00`))
    .filter((part) => part.type !== 'literal')
    .map((part) => part.value.replace(/\.$/, ''))
    .join(' ');
}

export function formatMonth(day: string): string {
  return monthFormat.format(new Date(`${day}T12:00:00-05:00`));
}

export function formatMonthAxis(day: string): string {
  return monthAxisFormat.format(new Date(`${day}T12:00:00-05:00`));
}

export function formatDayAxis(day: string): string {
  return dayAxisFormat
    .formatToParts(new Date(`${day}T12:00:00-05:00`))
    .filter((part) => part.type !== 'literal')
    .map((part) => part.value.replace(/\.$/, ''))
    .join(' ');
}

export function formatShortDateTime(iso: string): string {
  const moment = new Date(iso);
  return `${formatShortDate(isoDayFormat.format(moment))}, ${timeFormat.format(moment)}`;
}

export function formatInUnit(value: number, unit: FigureUnit): string {
  switch (unit) {
    case 'COP':
      return formatPesos(value);
    case 'percent':
      return formatPercent(value);
    case 'points':
      return formatPoints(value);
    case 'days':
      return formatDays(value);
    case 'units':
      return formatUnits(value);
  }
}

export function formatFigure(figure: Figure): string {
  return formatInUnit(figure.value, figure.unit);
}

export function formatFigureInText(figure: Figure): string {
  switch (figure.unit) {
    case 'COP':
      return formatCompactPesos(figure.value);
    case 'percent':
      return formatPercent(figure.value);
    default:
      return formatNumber(figure.value);
  }
}
