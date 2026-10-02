const NOMBRES: Record<string, string> = {
  destinatario: 'Destinatario',
  plazo_acuerdo_dias: 'Plazo del acuerdo de pago, en días',
  responsable: 'Responsable',
  unidades: 'Unidades',
  bodega: 'Bodega',
  origen: 'Bodega de origen',
  destino: 'Bodega de destino',
  alza_pct: 'Alza de precio, en %',
  reduccion_pedida_pct: 'Reducción de costo pedida, en %',
  duracion_dias: 'Duración, en días',
};

export function nombreParametro(clave: string): string {
  const nombre = NOMBRES[clave] ?? clave.replace(/_/g, ' ');
  return nombre.charAt(0).toUpperCase() + nombre.slice(1);
}
