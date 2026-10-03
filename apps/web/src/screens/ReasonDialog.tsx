import { useState } from 'react';
import { ArenaButton, ArenaDialog, ArenaTextarea } from '@dravensoft/arena-react';
import { ApiError } from '../api/client';

interface Props {
  open: boolean;
  eyebrow: string;
  title: string;
  hint: string;
  label: string;
  missing: string;
  failure: string;
  confirm: string;
  variant: 'danger' | 'primary';
  icon: string;
  onClose: () => void;
  onSend: (reason: string) => Promise<void>;
}

export function ReasonDialog({ open, eyebrow, title, hint, label, missing, failure, confirm, variant, icon, onClose, onSend }: Props) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | undefined>();
  const [sending, setSending] = useState(false);

  const close = () => {
    setReason('');
    setError(undefined);
    onClose();
  };

  const send = async () => {
    if (!reason.trim()) {
      setError(missing);
      return;
    }
    setSending(true);
    try {
      await onSend(reason.trim());
      setReason('');
      setError(undefined);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : failure);
    } finally {
      setSending(false);
    }
  };

  return (
    <ArenaDialog
      open={open}
      eyebrow={eyebrow}
      title={title}
      fillBelow="sm"
      onClose={close}
      footer={
        <>
          <ArenaButton variant="ghost" onClick={close}>
            Cancelar
          </ArenaButton>
          <ArenaButton variant={variant} icon={icon} loading={sending} onClick={send}>
            {confirm}
          </ArenaButton>
        </>
      }
    >
      <div className="arena-stack arena-stack--group">
        <p>{hint}</p>
        <ArenaTextarea
          label={label}
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
