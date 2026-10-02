import { cifraEnTexto, fecha } from '../formato';
import alertasJson from './fixtures/alertas.json';
import chatJson from './fixtures/chat.json';
import consultasJson from './fixtures/consultas.json';
import relojJson from './fixtures/reloj.json';
import type {
  Accion,
  Actor,
  Agente,
  Alerta,
  Cifra,
  Consulta,
  Decision,
  EstadoSimulacion,
  EventoAvance,
  EventoBitacora,
  EventoChat,
  FiltroAlertas,
  FiltroBitacora,
  Frase,
  MensajeChat,
  PasoAgente,
  PreguntaChat,
  PuntoSerie,
  TipoAccion,
  Usuario,
} from './types';

type AlertaFixture = Omit<Alerta, 'estado' | 'accionEjecutada'> & {
  guion: Record<'analista' | 'estratega', string>;
};

interface RespuestaChat {
  id: string;
  alertaId: string | null;
  palabras: string[];
  texto: string;
  cifras: Cifra[];
  serie?: PuntoSerie[];
  evidenciaSuficiente: boolean;
}

interface ChatFixture {
  respuestas: RespuestaChat[];
  sinEvidencia: Omit<RespuestaChat, 'id' | 'alertaId' | 'palabras'>;
}

interface RelojFixture {
  diaInicial: string;
  usuario: Usuario;
}

export class ErrorApi extends Error {
  constructor(
    readonly estado: 404 | 409 | 422,
    message: string,
  ) {
    super(message);
    this.name = 'ErrorApi';
  }
}

const RETRASO_PASO_MS = 900;
const RETRASO_FRAGMENTO_MS = 45;

const RESULTADO_POR_TIPO: Record<TipoAccion, string> = {
  borrador_correo: 'Borrador de correo guardado; queda sin enviar hasta que una persona lo envíe',
  tarea: 'Tarea creada y asignada',
  borrador_orden_compra: 'Borrador de orden de compra guardado; queda sin emitir',
  borrador_ajuste_precio: 'Borrador de ajuste de precio guardado; la lista de precios no cambia hasta publicarlo',
};

const reloj = relojJson as RelojFixture;
const fixtures = (alertasJson as unknown as AlertaFixture[]).map(resolverAlerta);
const consultas = new Map((consultasJson as Consulta[]).map((c) => [c.id, c]));
const respuestasChat = chatJson as unknown as ChatFixture;

let diaSimulado = reloj.diaInicial;
const alertas = new Map<string, Alerta>();
const bitacoraEventos: EventoBitacora[] = [];
let secuencia = 0;

for (const fixture of fixtures.filter((f) => f.fechaSimulada <= diaSimulado)) {
  const alerta = crearAlerta(fixture, 'propuesta');
  registrarDeteccion(alerta);
  registrarAnalisis(alerta);
  registrarPropuesta(alerta);
}

export async function estadoSimulacion(): Promise<EstadoSimulacion> {
  return { diaSimulado, usuario: { ...reloj.usuario } };
}

export async function* avanzarDia(dias = 1): AsyncGenerator<EventoAvance> {
  const alertasNuevas: string[] = [];
  for (let i = 0; i < dias; i++) {
    diaSimulado = sumarDias(diaSimulado, 1);
    const delDia = fixtures.filter((f) => f.fechaSimulada === diaSimulado);

    const vigia = iniciarPaso(null, 'vigia', `Revisando los indicadores del ${fecha(diaSimulado)}`);
    yield { evento: 'paso', datos: { ...vigia } };
    await esperar(RETRASO_PASO_MS);
    terminarPaso(
      vigia,
      delDia.length === 0
        ? 'Sin hallazgos: todos los indicadores están dentro de sus umbrales'
        : `Encontré algo que decidir: ${delDia.map((f) => f.titulo.texto).join('; ')}`,
    );
    yield { evento: 'paso', datos: { ...vigia } };

    for (const fixture of delDia) {
      const alerta = crearAlerta(fixture, 'nueva');
      alertasNuevas.push(alerta.id);
      registrarDeteccion(alerta);
      yield { evento: 'alerta', datos: copiar(alerta) };

      alerta.estado = 'en_analisis';
      const analista = iniciarPaso(alerta.id, 'analista', fixture.guion.analista);
      yield { evento: 'paso', datos: { ...analista } };
      yield { evento: 'alerta', datos: copiar(alerta) };
      await esperar(RETRASO_PASO_MS);
      registrarAnalisis(alerta);
      terminarPaso(analista, fixture.causa.tipo === 'identificada' ? 'Causa identificada' : 'Sin evidencia suficiente para una causa');
      yield { evento: 'paso', datos: { ...analista } };

      const estratega = iniciarPaso(alerta.id, 'estratega', fixture.guion.estratega);
      yield { evento: 'paso', datos: { ...estratega } };
      await esperar(RETRASO_PASO_MS);
      alerta.estado = 'propuesta';
      registrarPropuesta(alerta);
      terminarPaso(estratega, 'Propuesta lista para decidir');
      yield { evento: 'paso', datos: { ...estratega } };
      yield { evento: 'alerta', datos: copiar(alerta) };
    }
  }
  yield { evento: 'fin', datos: { diaSimulado, alertasNuevas } };
}

export async function listarAlertas(filtro: FiltroAlertas = {}): Promise<Alerta[]> {
  return [...alertas.values()]
    .filter((a) => !filtro.estado || a.estado === filtro.estado)
    .sort((a, b) => b.pesosEnRiesgo.valor - a.pesosEnRiesgo.valor)
    .map(copiar);
}

export async function obtenerAlerta(id: string): Promise<Alerta> {
  return copiar(buscarAlerta(id));
}

export async function decidir(id: string, decision: Decision): Promise<Alerta> {
  const alerta = buscarAlerta(id);
  if (alerta.estado !== 'propuesta') {
    throw new ErrorApi(409, 'Esta alerta ya no espera una decisión');
  }
  const persona: Actor = { tipo: 'persona', ...reloj.usuario };

  if (decision.tipo === 'rechazar') {
    const motivo = decision.motivo.trim();
    if (!motivo) {
      throw new ErrorApi(422, 'Para rechazar hace falta un motivo');
    }
    alerta.estado = 'rechazada';
    registrar(alerta.id, 'decision', persona, `Rechazada. Motivo: ${motivo}`);
    return copiar(alerta);
  }

  const accion = alerta.acciones.find((a) => a.id === decision.accionId);
  if (!accion) {
    throw new ErrorApi(422, 'La acción elegida no pertenece a esta alerta');
  }
  if (decision.tipo === 'editar') {
    accion.parametros = { ...accion.parametros, ...decision.parametros };
  }
  alerta.estado = 'aprobada';
  registrar(alerta.id, 'decision', persona, describirAprobacion(accion, decision));

  await esperar(RETRASO_PASO_MS);
  const ejecutor: Actor = { tipo: 'agente', agente: 'ejecutor' };
  const detalleAccion =
    decision.tipo === 'editar'
      ? `${accion.titulo}, con ${describirParametros(decision.parametros)}`
      : `${accion.titulo}: ${accion.descripcion.texto}`;
  registrar(alerta.id, 'accion', ejecutor, detalleAccion);
  const resultado = RESULTADO_POR_TIPO[accion.tipo];
  alerta.estado = 'ejecutada';
  alerta.accionEjecutada = { accionId: accion.id, resultado };
  registrar(alerta.id, 'resultado', ejecutor, resultado);
  return copiar(alerta);
}

export async function* chat({ pregunta, alertaId }: PreguntaChat): AsyncGenerator<EventoChat> {
  const respuesta = elegirRespuesta(pregunta, alertaId);
  const paso = iniciarPaso(alertaId ?? null, 'analista', 'Buscando la respuesta en los datos');
  yield { evento: 'paso', datos: { ...paso } };
  await esperar(RETRASO_PASO_MS);
  terminarPaso(paso, respuesta.evidenciaSuficiente ? 'Respuesta encontrada' : 'Sin evidencia suficiente');
  yield { evento: 'paso', datos: { ...paso } };

  const texto = rellenar(respuesta.texto, respuesta.cifras);
  for (const fragmento of texto.split(/(?<=\s)/)) {
    await esperar(RETRASO_FRAGMENTO_MS);
    yield { evento: 'fragmento', datos: { texto: fragmento } };
  }

  const mensaje: MensajeChat = {
    id: siguienteId('msg'),
    rol: 'centinela',
    texto,
    cifras: structuredClone(respuesta.cifras),
    evidenciaSuficiente: respuesta.evidenciaSuficiente,
    fecha: new Date().toISOString(),
    ...(alertaId ? { alertaId } : {}),
    ...(respuesta.serie ? { serie: structuredClone(respuesta.serie) } : {}),
  };
  yield { evento: 'fin', datos: mensaje };
}

export async function bitacora(filtro: FiltroBitacora = {}): Promise<EventoBitacora[]> {
  return bitacoraEventos
    .filter((e) => (!filtro.alertaId || e.alertaId === filtro.alertaId) && (!filtro.tipo || e.tipo === filtro.tipo))
    .reverse()
    .map((e) => structuredClone(e));
}

export async function consulta(id: string): Promise<Consulta> {
  const encontrada = consultas.get(id);
  if (!encontrada) {
    throw new ErrorApi(404, 'No existe esa consulta');
  }
  return { ...encontrada };
}

function crearAlerta(fixture: AlertaFixture, estado: Alerta['estado']): Alerta {
  const { guion: _guion, ...datos } = structuredClone(fixture);
  const alerta: Alerta = { ...datos, estado };
  alertas.set(alerta.id, alerta);
  return alerta;
}

function buscarAlerta(id: string): Alerta {
  const alerta = alertas.get(id);
  if (!alerta) {
    throw new ErrorApi(404, 'No existe esa alerta');
  }
  return alerta;
}

function registrarDeteccion(alerta: Alerta) {
  registrar(alerta.id, 'alerta', { tipo: 'agente', agente: 'vigia' }, alerta.titulo.texto, alerta.titulo.cifras[0]?.consultaId);
}

function registrarAnalisis(alerta: Alerta) {
  const analista: Actor = { tipo: 'agente', agente: 'analista' };
  if (alerta.causa.tipo === 'sin_evidencia') {
    registrar(alerta.id, 'evidencia', analista, alerta.causa.motivo);
    return;
  }
  for (const evidencia of alerta.causa.evidencia) {
    registrar(alerta.id, 'evidencia', analista, evidencia.afirmacion.texto, evidencia.consultaId);
  }
}

function registrarPropuesta(alerta: Alerta) {
  const titulos = alerta.acciones.map((a) => a.titulo).join('; ');
  registrar(alerta.id, 'propuesta', { tipo: 'agente', agente: 'estratega' }, titulos);
}

function registrar(
  alertaId: string,
  tipo: EventoBitacora['tipo'],
  actor: Actor,
  detalle: string,
  consultaId?: string,
) {
  bitacoraEventos.push({
    id: siguienteId('ev'),
    fecha: new Date().toISOString(),
    diaSimulado,
    alertaId,
    tipo,
    actor,
    detalle,
    ...(consultaId ? { consultaId } : {}),
  });
}

function describirAprobacion(accion: Accion, decision: Decision): string {
  if (decision.tipo !== 'editar') {
    return `Aprobada: ${accion.titulo}`;
  }
  return `Aprobada con cambios: ${accion.titulo} (${describirParametros(decision.parametros)})`;
}

function describirParametros(parametros: Record<string, string | number>): string {
  return Object.entries(parametros)
    .map(([clave, valor]) => `${clave} = ${valor}`)
    .join(', ');
}

function iniciarPaso(alertaId: string | null, agente: Agente, descripcion: string): PasoAgente {
  return { alertaId, agente, estado: 'en_curso', descripcion, inicio: new Date().toISOString() };
}

function terminarPaso(paso: PasoAgente, descripcion: string) {
  paso.estado = 'hecho';
  paso.descripcion = descripcion;
  paso.fin = new Date().toISOString();
}

function elegirRespuesta(pregunta: string, alertaId?: string): Omit<RespuestaChat, 'id' | 'alertaId' | 'palabras'> {
  const texto = normalizar(pregunta);
  const candidatas = respuestasChat.respuestas.filter(
    (r) => (r.alertaId === null || r.alertaId === alertaId) && r.palabras.every((p) => texto.includes(normalizar(p))),
  );
  return candidatas.find((r) => r.alertaId !== null) ?? candidatas[0] ?? respuestasChat.sinEvidencia;
}

function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

function resolverAlerta(fixture: AlertaFixture): AlertaFixture {
  const causa: AlertaFixture['causa'] =
    fixture.causa.tipo === 'identificada'
      ? {
          ...fixture.causa,
          frase: resolverFrase(fixture.causa.frase),
          evidencia: fixture.causa.evidencia.map((e) => ({ ...e, afirmacion: resolverFrase(e.afirmacion) })),
        }
      : fixture.causa;
  return {
    ...fixture,
    titulo: resolverFrase(fixture.titulo),
    causa,
    acciones: fixture.acciones.map((a) => ({ ...a, descripcion: resolverFrase(a.descripcion) })) as Alerta['acciones'],
  };
}

function resolverFrase(frase: Frase): Frase {
  return { ...frase, texto: rellenar(frase.texto, frase.cifras) };
}

function rellenar(texto: string, cifras: Cifra[]): string {
  return texto.replace(/\{(\d+)\}/g, (marcador, indice: string) => {
    const c = cifras[Number(indice)];
    return c ? cifraEnTexto(c) : marcador;
  });
}

function sumarDias(dia: string, n: number): string {
  const d = new Date(`${dia}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function siguienteId(prefijo: string): string {
  secuencia += 1;
  return `${prefijo}-${secuencia}`;
}

function copiar(alerta: Alerta): Alerta {
  return structuredClone(alerta);
}

function esperar(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
