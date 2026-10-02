import { useEffect, useState } from 'react';
import { ArenaButton, ArenaDialog, ArenaInput } from '@dravensoft/arena-react';
import { ErrorApi } from '../api/client';
import type { Accion } from '../api/types';
import { nombreParametro } from './parametros';

interface Props {
  accion: Accion;
  abierto: boolean;
  onCerrar: () => void;
  onAprobar: (parametros: Record<string, string | number>) => Promise<void>;
}

export function DialogoEditar({ accion, abierto, onCerrar, onAprobar }: Props) {
  const [valores, setValores] = useState<Record<string, string>>({});
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorGeneral, setErrorGeneral] = useState<string | undefined>();
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (abierto) {
      setValores(Object.fromEntries(Object.entries(accion.parametros).map(([clave, valor]) => [clave, String(valor)])));
      setErrores({});
      setErrorGeneral(undefined);
    }
  }, [abierto, accion]);

  const aprobar = async () => {
    const nuevosErrores: Record<string, string> = {};
    const parametros: Record<string, string | number> = {};
    for (const [clave, original] of Object.entries(accion.parametros)) {
      const texto = (valores[clave] ?? '').trim();
      if (!texto) {
        nuevosErrores[clave] = 'Este dato no puede quedar vacío.';
      } else if (typeof original === 'number') {
        const numero = Number(texto);
        if (Number.isNaN(numero) || numero < 0) {
          nuevosErrores[clave] = 'Escribe un número mayor o igual a cero.';
        } else {
          parametros[clave] = numero;
        }
      } else {
        parametros[clave] = texto;
      }
    }
    setErrores(nuevosErrores);
    if (Object.keys(nuevosErrores).length > 0) {
      return;
    }
    setEnviando(true);
    try {
      await onAprobar(parametros);
    } catch (e) {
      setErrorGeneral(e instanceof ErrorApi ? e.message : 'No se pudo aprobar. Inténtalo de nuevo.');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <ArenaDialog
      open={abierto}
      eyebrow="Editar antes de aprobar"
      title={accion.titulo}
      fillBelow="sm"
      onClose={onCerrar}
      footer={
        <>
          <ArenaButton variant="ghost" onClick={onCerrar}>
            Cancelar
          </ArenaButton>
          <ArenaButton variant="primary" icon="ph-bold ph-check" loading={enviando} onClick={aprobar}>
            Aprobar con cambios
          </ArenaButton>
        </>
      }
    >
      <div className="arena-stack">
        <p>Ajusta los datos de la acción. Se aprueba con tus cambios y queda registrada en la bitácora.</p>
        {Object.entries(accion.parametros).map(([clave, original]) => (
          <ArenaInput
            key={clave}
            id={`param-${clave}`}
            label={nombreParametro(clave)}
            type={typeof original === 'number' ? 'number' : 'text'}
            min={typeof original === 'number' ? '0' : undefined}
            value={valores[clave] ?? ''}
            error={errores[clave]}
            onChange={(texto) => setValores((v) => ({ ...v, [clave]: texto }))}
          />
        ))}
        {errorGeneral ? <p role="alert">{errorGeneral}</p> : null}
      </div>
    </ArenaDialog>
  );
}
