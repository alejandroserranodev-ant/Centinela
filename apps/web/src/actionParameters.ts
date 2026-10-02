const NAMES: Record<string, string> = {
  recipient: 'Destinatario',
  agreement_term_days: 'Plazo del acuerdo de pago, en días',
  owner: 'Responsable',
  units: 'Unidades',
  warehouse: 'Bodega',
  origin: 'Bodega de origen',
  destination: 'Bodega de destino',
  price_increase_pct: 'Alza de precio, en %',
  requested_reduction_pct: 'Reducción de costo pedida, en %',
  duration_days: 'Duración, en días',
};

export function parameterName(key: string): string {
  const name = NAMES[key] ?? key.replace(/_/g, ' ');
  return name.charAt(0).toUpperCase() + name.slice(1);
}
