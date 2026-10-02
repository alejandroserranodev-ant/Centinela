import { useState } from 'react';
import { ArenaButton, ArenaDialog, ArenaTextarea } from '@dravensoft/arena-react';
import { ErrorApi } from '../api/client';

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  onRechazar: (motivo: string) => Promise<void>;
}

export function DialogoRechazo({ abierto, onCerrar, onRechazar }: Props) {
  const [motivo, setMotivo] = useState('');
  const [error, setError] = useState<string | undefined>();
  const [enviando, setEnviando] = useState(false);

  const cerrar = () => {
    setMotivo('');
    setError(undefined);
    onCerrar();
  };

  const rechazar = async () => {
    if (!motivo.trim()) {
      setError('Escribe el motivo del rechazo para continuar.');
      return;
    }
    setEnviando(true);
    try {
      await onRechazar(motivo.trim());
      setMotivo('');
      setError(undefined);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : 'No se pudo registrar el rechazo. Inténtalo de nuevo.');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <ArenaDialog
      open={abierto}
      eyebrow="Rechazar"
      title="¿Por qué rechazas la propuesta?"
      fillBelow="sm"
      onClose={cerrar}
      footer={
        <>
          <ArenaButton variant="ghost" onClick={cerrar}>
            Cancelar
          </ArenaButton>
          <ArenaButton variant="danger" icon="ph-bold ph-x" loading={enviando} onClick={rechazar}>
            Rechazar
          </ArenaButton>
        </>
      }
    >
      <div className="arena-stack arena-stack--group">
        <p>El motivo queda en la bitácora junto a tu nombre y sirve para ajustar las próximas propuestas.</p>
        <ArenaTextarea
          label="Motivo del rechazo"
          required
          rows={4}
          maxLength={500}
          counter
          value={motivo}
          error={error}
          onChange={(texto) => {
            setMotivo(texto);
            if (texto.trim()) {
              setError(undefined);
            }
          }}
        />
      </div>
    </ArenaDialog>
  );
}
