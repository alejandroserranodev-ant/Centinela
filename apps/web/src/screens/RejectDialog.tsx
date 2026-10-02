import { useState } from 'react';
import { ArenaButton, ArenaDialog, ArenaTextarea } from '@dravensoft/arena-react';
import { ApiError } from '../api/client';

interface Props {
  open: boolean;
  onClose: () => void;
  onReject: (reason: string) => Promise<void>;
}

export function RejectDialog({ open, onClose, onReject }: Props) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | undefined>();
  const [sending, setSending] = useState(false);

  const close = () => {
    setReason('');
    setError(undefined);
    onClose();
  };

  const reject = async () => {
    if (!reason.trim()) {
      setError('Escribe el motivo del rechazo para continuar.');
      return;
    }
    setSending(true);
    try {
      await onReject(reason.trim());
      setReason('');
      setError(undefined);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo registrar el rechazo. Inténtalo de nuevo.');
    } finally {
      setSending(false);
    }
  };

  return (
    <ArenaDialog
      open={open}
      eyebrow="Rechazar"
      title="¿Por qué rechazas la propuesta?"
      fillBelow="sm"
      onClose={close}
      footer={
        <>
          <ArenaButton variant="ghost" onClick={close}>
            Cancelar
          </ArenaButton>
          <ArenaButton variant="danger" icon="ph-bold ph-x" loading={sending} onClick={reject}>
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
          value={reason}
          error={error}
          onChange={(text) => {
            setReason(text);
            if (text.trim()) {
              setError(undefined);
            }
          }}
        />
      </div>
    </ArenaDialog>
  );
}
