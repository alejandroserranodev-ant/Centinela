export type EstadoAlerta = 'nueva' | 'en_analisis' | 'propuesta' | 'aprobada' | 'rechazada' | 'ejecutada';

export type Severidad = 'critica' | 'alta' | 'media' | 'baja';

export type NivelConfianza = 'alta' | 'media' | 'baja';

export type Metrica =
  | 'margen_pct'
  | 'saldo_vencido'
  | 'dias_pago_prom'
  | 'cobertura_dias'
  | 'descuento_en_exceso'
  | 'veces_intervalo_habitual';

export type VistaSemantica =
  | 'v_ventas'
  | 'v_margen_semanal_linea'
  | 'v_cartera_cliente'
  | 'v_dias_pago_mensual'
  | 'v_cobertura_inventario'
  | 'v_descuentos_fuera_politica'
  | 'v_actividad_cliente';

export interface Consulta {
  id: string;
  vista: VistaSemantica;
  sql: string;
  descripcion: string;
}

export type UnidadCifra = 'COP' | 'puntos' | 'porcentaje' | 'dias' | 'unidades';

export interface Cifra {
  valor: number;
  unidad: UnidadCifra;
  consultaId: string;
}

export interface Frase {
  texto: string;
  cifras: Cifra[];
}

export interface Confianza {
  nivel: NivelConfianza;
  supuestos: string[];
}

export interface PuntoSerie {
  fecha: string;
  valor: number;
}

export interface Evidencia {
  afirmacion: Frase;
  consultaId: string;
  serie?: PuntoSerie[];
}

export type Causa =
  | { tipo: 'identificada'; frase: Frase; evidencia: Evidencia[] }
  | { tipo: 'sin_evidencia'; motivo: string; consultasRevisadas: string[] };

export type TipoAccion = 'borrador_correo' | 'tarea' | 'borrador_orden_compra' | 'borrador_ajuste_precio';

export interface Impacto {
  cifra: Cifra;
  periodo: 'mes' | 'unico';
}

export interface Accion {
  id: string;
  titulo: string;
  descripcion: Frase;
  tipo: TipoAccion;
  impacto: Impacto | null;
  confianza: Confianza;
  parametros: Record<string, string | number>;
}

export type Acciones = [Accion] | [Accion, Accion] | [Accion, Accion, Accion];

export interface AccionEjecutada {
  accionId: string;
  resultado: string;
}

export interface Alerta {
  id: string;
  estado: EstadoAlerta;
  severidad: Severidad;
  metrica: Metrica;
  titulo: Frase;
  pesosEnRiesgo: Cifra;
  recuperableMes: Cifra | null;
  confianza: Confianza;
  fechaSimulada: string;
  causa: Causa;
  acciones: Acciones;
  accionEjecutada?: AccionEjecutada;
}

export type Agente = 'vigia' | 'analista' | 'estratega' | 'ejecutor';

export interface PasoAgente {
  alertaId: string | null;
  agente: Agente;
  estado: 'en_curso' | 'hecho';
  descripcion: string;
  inicio: string;
  fin?: string;
}

export interface Usuario {
  nombre: string;
  rol: string;
}

export type Actor = { tipo: 'agente'; agente: Agente } | ({ tipo: 'persona' } & Usuario);

export type TipoEventoBitacora = 'alerta' | 'evidencia' | 'propuesta' | 'decision' | 'accion' | 'resultado';

export interface EventoBitacora {
  id: string;
  fecha: string;
  diaSimulado: string;
  alertaId: string;
  tipo: TipoEventoBitacora;
  actor: Actor;
  detalle: string;
  consultaId?: string;
}

export interface MensajeChat {
  id: string;
  rol: 'usuario' | 'centinela';
  texto: string;
  cifras: Cifra[];
  alertaId?: string;
  serie?: PuntoSerie[];
  evidenciaSuficiente: boolean;
  fecha: string;
}

export interface EventoSSE<E extends string, D> {
  evento: E;
  datos: D;
}

export type EventoAvance =
  | EventoSSE<'paso', PasoAgente>
  | EventoSSE<'alerta', Alerta>
  | EventoSSE<'fin', { diaSimulado: string; alertasNuevas: string[] }>;

export type EventoChat =
  | EventoSSE<'paso', PasoAgente>
  | EventoSSE<'fragmento', { texto: string }>
  | EventoSSE<'fin', MensajeChat>;

export type Decision =
  | { tipo: 'aprobar'; accionId: string }
  | { tipo: 'editar'; accionId: string; parametros: Record<string, string | number> }
  | { tipo: 'rechazar'; motivo: string };

export interface PreguntaChat {
  pregunta: string;
  alertaId?: string;
}

export interface FiltroAlertas {
  estado?: EstadoAlerta;
}

export interface FiltroBitacora {
  alertaId?: string;
  tipo?: TipoEventoBitacora;
}

export interface EstadoSimulacion {
  diaSimulado: string;
  usuario: Usuario;
}
