import { useEffect, useState } from 'react';
import { ArenaButton, ArenaDialog, ArenaInput } from '@dravensoft/arena-react';
import { ApiError } from '../api/client';
import type { Action } from '../api/types';
import { parameterName } from './actionParameters';

interface Props {
  action: Action;
  open: boolean;
  onClose: () => void;
  onApprove: (parameters: Record<string, string | number>) => Promise<void>;
}

export function EditDialog({ action, open, onClose, onApprove }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | undefined>();
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (open) {
      setValues(Object.fromEntries(Object.entries(action.parameters).map(([key, value]) => [key, String(value)])));
      setErrors({});
      setGeneralError(undefined);
    }
  }, [open, action]);

  const approve = async () => {
    const nextErrors: Record<string, string> = {};
    const parameters: Record<string, string | number> = {};
    for (const [key, original] of Object.entries(action.parameters)) {
      const text = (values[key] ?? '').trim();
      if (!text) {
        nextErrors[key] = 'Este dato no puede quedar vacío.';
      } else if (typeof original === 'number') {
        const number = Number(text);
        if (Number.isNaN(number) || number < 0) {
          nextErrors[key] = 'Escribe un número mayor o igual a cero.';
        } else {
          parameters[key] = number;
        }
      } else {
        parameters[key] = text;
      }
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }
    setSending(true);
    try {
      await onApprove(parameters);
    } catch (e) {
      setGeneralError(e instanceof ApiError ? e.message : 'No se pudo aprobar. Inténtalo de nuevo.');
    } finally {
      setSending(false);
    }
  };

  return (
    <ArenaDialog
      open={open}
      eyebrow="Editar antes de aprobar"
      title={action.title}
      fillBelow="sm"
      onClose={onClose}
      footer={
        <>
          <ArenaButton variant="ghost" onClick={onClose}>
            Cancelar
          </ArenaButton>
          <ArenaButton variant="primary" icon="ph-bold ph-check" loading={sending} onClick={approve}>
            Aprobar con cambios
          </ArenaButton>
        </>
      }
    >
      <div className="arena-stack">
        <p>Ajusta los datos de la acción. Se aprueba con tus cambios y queda registrada en la bitácora.</p>
        {Object.entries(action.parameters).map(([key, original]) => (
          <ArenaInput
            key={key}
            id={`param-${key}`}
            label={parameterName(key)}
            type={typeof original === 'number' ? 'number' : 'text'}
            min={typeof original === 'number' ? '0' : undefined}
            value={values[key] ?? ''}
            error={errors[key]}
            onChange={(text) => setValues((v) => ({ ...v, [key]: text }))}
          />
        ))}
        {generalError ? <p role="alert">{generalError}</p> : null}
      </div>
    </ArenaDialog>
  );
}
