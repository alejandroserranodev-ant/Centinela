import { ArenaChartCard, ArenaKeyValue, ArenaLineChart } from '@dravensoft/arena-react';
import type { ArenaNumberFormat } from '@dravensoft/arena-react';
import type { FuenteConsulta, PuntoSerie, UnidadCifra } from '../api/types';
import { ejeDia, ejeMes, enUnidad, fecha, mes } from '../formato';

interface Escala {
  prefijo?: string;
  sufijo?: string;
  formato: ArenaNumberFormat;
}

const ESCALA: Record<UnidadCifra, Escala> = {
  COP: { prefijo: '$ ', formato: { locale: 'es-CO', compact: true } },
  porcentaje: { sufijo: ' %', formato: { locale: 'es-CO' } },
  puntos: { sufijo: ' pts', formato: { locale: 'es-CO' } },
  dias: { sufijo: ' días', formato: { locale: 'es-CO', fractionDigits: 0 } },
  unidades: { formato: { locale: 'es-CO', fractionDigits: 0 } },
};

const TITULO_POR_FUENTE: Record<FuenteConsulta, string> = {
  v_ventas: 'Ventas',
  v_margen_semanal_linea: 'Margen semanal',
  v_cartera_cliente: 'Cartera',
  v_dias_pago_mensual: 'Días de pago por mes',
  v_cobertura_inventario: 'Cobertura de inventario',
  v_descuentos_fuera_politica: 'Descuentos fuera de política',
  v_actividad_cliente: 'Actividad del cliente',
  alertas: 'Alertas',
};

export function tituloDeFuente(fuente: FuenteConsulta): string {
  return TITULO_POR_FUENTE[fuente];
}

interface Props {
  titulo: string;
  nombre: string;
  serie: PuntoSerie[];
  unidad: UnidadCifra;
  alto?: number;
}

export function GraficoSerie({ titulo, nombre, serie, unidad, alto }: Props) {
  const mensual = serie.every((p) => p.fecha.endsWith('-01'));
  const etiquetas = serie.map((p) => (mensual ? ejeMes(p.fecha) : ejeDia(p.fecha)));
  const fechas = serie.map((p) => (mensual ? mes(p.fecha) : fecha(p.fecha)));
  const escala = ESCALA[unidad];
  return (
    <ArenaChartCard title={titulo}>
      <div className="arena-stack arena-stack--group">
        <div className="grafico">
          <ArenaLineChart
          label={nombre}
          labels={etiquetas}
          series={[{ label: titulo, values: serie.map((p) => p.valor), slot: 1 }]}
          valueFormat={escala.formato}
          valuePrefix={escala.prefijo}
          valueSuffix={escala.sufijo}
          height={alto}
            minPointSpacing={44}
          />
        </div>
        <details className="plegable">
          <summary>Ver los datos</summary>
          <ArenaKeyValue
            rows={serie.map((p, i) => ({ term: fechas[i], value: enUnidad(p.valor, unidad), numeric: true }))}
          />
        </details>
      </div>
    </ArenaChartCard>
  );
}
