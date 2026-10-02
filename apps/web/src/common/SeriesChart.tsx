import { ArenaChartCard, ArenaKeyValue, ArenaLineChart } from '@dravensoft/arena-react';
import type { ArenaNumberFormat } from '@dravensoft/arena-react';
import type { FigureUnit, QuerySource, SeriesPoint } from '../api/types';
import { formatDate, formatDayAxis, formatInUnit, formatMonth, formatMonthAxis } from '../format';

interface Scale {
  prefix?: string;
  suffix?: string;
  format: ArenaNumberFormat;
}

const SCALE: Record<FigureUnit, Scale> = {
  COP: { prefix: '$ ', format: { locale: 'es-CO', compact: true } },
  percent: { suffix: ' %', format: { locale: 'es-CO' } },
  points: { suffix: ' pts', format: { locale: 'es-CO' } },
  days: { suffix: ' días', format: { locale: 'es-CO', fractionDigits: 0 } },
  units: { format: { locale: 'es-CO', fractionDigits: 0 } },
};

const TITLE_BY_SOURCE: Record<QuerySource, string> = {
  v_ventas: 'Ventas',
  v_margen_semanal_linea: 'Margen semanal',
  v_cartera_cliente: 'Cartera',
  v_dias_pago_mensual: 'Días de pago por mes',
  v_cobertura_inventario: 'Cobertura de inventario',
  v_descuentos_fuera_politica: 'Descuentos fuera de política',
  v_actividad_cliente: 'Actividad del cliente',
  alertas: 'Alertas',
};

export function sourceTitle(source: QuerySource): string {
  return TITLE_BY_SOURCE[source];
}

interface Props {
  title: string;
  name: string;
  series: SeriesPoint[];
  unit: FigureUnit;
  height?: number;
}

export function SeriesChart({ title, name, series, unit, height }: Props) {
  const monthly = series.every((p) => p.date.endsWith('-01'));
  const labels = series.map((p) => (monthly ? formatMonthAxis(p.date) : formatDayAxis(p.date)));
  const dates = series.map((p) => (monthly ? formatMonth(p.date) : formatDate(p.date)));
  const scale = SCALE[unit];
  return (
    <ArenaChartCard title={title}>
      <div className="arena-stack arena-stack--group">
        <div className="chart">
          <ArenaLineChart
            label={name}
            labels={labels}
            series={[{ label: title, values: series.map((p) => p.value), slot: 1 }]}
            valueFormat={scale.format}
            valuePrefix={scale.prefix}
            valueSuffix={scale.suffix}
            height={height}
            minPointSpacing={44}
          />
        </div>
        <details className="collapsible">
          <summary>Ver los datos</summary>
          <ArenaKeyValue rows={series.map((p, i) => ({ term: dates[i], value: formatInUnit(p.value, unit), numeric: true }))} />
        </details>
      </div>
    </ArenaChartCard>
  );
}
