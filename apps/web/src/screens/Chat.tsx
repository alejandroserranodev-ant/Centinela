import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import {
  ArenaAlert,
  ArenaButton,
  ArenaSheet,
  ArenaSpinner,
  ArenaTag,
  ArenaTextarea,
  useArenaViewportBelow,
} from '@dravensoft/arena-react';
import { chat, getAlert, getQuery } from '../api/client';
import type { ChatMessage, Query } from '../api/types';
import { SentenceWithFigures } from '../common/SentenceWithFigures';
import { SeriesChart, sourceTitle } from '../common/SeriesChart';
import { useSimulation } from '../state/Simulation';

const FIELD_ID = 'chat-question';

type Entry =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'centinela'; status: 'searching' | 'writing'; step: string; text: string }
  | { id: number; role: 'centinela'; status: 'ready'; message: ChatMessage }
  | { id: number; role: 'centinela'; status: 'error' };

const ALERT_SUGGESTIONS: Record<string, string[]> = {
  'alert-hogar-margin': ['¿Qué clientes compran esos SKU?'],
};

const GLOBAL_SUGGESTIONS = ['¿Cómo va el margen de Hogar?', '¿Cuál es la tasa de cambio del dólar hoy?'];

function MessageChart({ message }: { message: ChatMessage }) {
  const [source, setSource] = useState<Query | null>(null);
  const first = message.figures[0];
  useEffect(() => {
    if (first) {
      getQuery(first.queryId).then(setSource, () => setSource(null));
    }
  }, [first]);
  if (!message.series || !first || !source) {
    return null;
  }
  return (
    <SeriesChart title={sourceTitle(source.source)} name={source.description} series={message.series} unit={first.unit} height={160} />
  );
}

function Answer({ entry }: { entry: Exclude<Entry, { role: 'user' }> }) {
  if (entry.status === 'error') {
    return (
      <ArenaAlert tone="danger" title="No pude responder">
        Intenta de nuevo en unos segundos.
      </ArenaAlert>
    );
  }
  if (entry.status !== 'ready') {
    return (
      <div className="arena-stack arena-stack--group" aria-busy="true">
        {entry.text ? <p>{entry.text}</p> : null}
        {entry.status === 'searching' ? <ArenaSpinner size="sm" label={entry.step} /> : null}
      </div>
    );
  }
  const { message } = entry;
  if (!message.enoughEvidence) {
    return (
      <ArenaAlert tone="info" icon="ph-bold ph-question" title="Sin evidencia suficiente">
        <SentenceWithFigures text={message.text} figures={message.figures} />
      </ArenaAlert>
    );
  }
  return (
    <div className="arena-stack arena-stack--group">
      <p>
        <SentenceWithFigures text={message.text} figures={message.figures} />
      </p>
      <MessageChart message={message} />
    </div>
  );
}

export function Chat() {
  const mobile = useArenaViewportBelow('lg');
  const { chat: state, closeChat, clearChatContext } = useSimulation();
  const [entries, setEntries] = useState<Entry[]>([]);
  const [question, setQuestion] = useState('');
  const [answering, setAnswering] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [alertTitle, setAlertTitle] = useState<string | null>(null);
  const conversation = useRef<HTMLOListElement>(null);
  const origin = useRef<HTMLElement | null>(null);
  const next = useRef(0);

  useEffect(() => {
    setAlertTitle(null);
    if (state.alertId) {
      getAlert(state.alertId).then(
        (a) => setAlertTitle(a.title.text),
        () => setAlertTitle(null),
      );
    }
  }, [state.alertId]);

  useEffect(() => {
    if (state.open) {
      origin.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setCollapsed(false);
      const frame = requestAnimationFrame(() => document.getElementById(FIELD_ID)?.focus());
      return () => cancelAnimationFrame(frame);
    }
    origin.current?.focus();
    origin.current = null;
    return undefined;
  }, [state.open]);

  useEffect(() => {
    conversation.current?.lastElementChild?.scrollIntoView({ block: 'end' });
  }, [entries]);

  const update = (id: number, change: (e: Entry) => Entry) =>
    setEntries((current) => current.map((e) => (e.id === id ? change(e) : e)));

  const ask = async (text: string) => {
    const clean = text.trim();
    if (!clean || answering) {
      return;
    }
    next.current += 2;
    const questionId = next.current - 1;
    const answerId = next.current;
    setQuestion('');
    setAnswering(true);
    setEntries((current) => [
      ...current,
      { id: questionId, role: 'user', text: clean },
      { id: answerId, role: 'centinela', status: 'searching', step: 'Buscando la respuesta', text: '' },
    ]);
    try {
      for await (const event of chat({ question: clean, ...(state.alertId ? { alertId: state.alertId } : {}) })) {
        if (event.event === 'step') {
          const step = event.data.description;
          update(answerId, (e) => (e.role === 'centinela' && e.status === 'searching' ? { ...e, step } : e));
        } else if (event.event === 'chunk') {
          const chunk = event.data.text;
          update(answerId, (e) =>
            e.role === 'centinela' && (e.status === 'searching' || e.status === 'writing')
              ? { ...e, status: 'writing', text: e.text + chunk }
              : e,
          );
        } else {
          const message = event.data;
          update(answerId, () => ({ id: answerId, role: 'centinela', status: 'ready', message }));
        }
      }
    } catch {
      update(answerId, () => ({ id: answerId, role: 'centinela', status: 'error' }));
    } finally {
      setAnswering(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void ask(question);
  };

  const keys = (event: KeyboardEvent<HTMLFormElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && event.target instanceof HTMLTextAreaElement) {
      event.preventDefault();
      void ask(question);
    }
  };

  const suggestions = state.alertId ? (ALERT_SUGGESTIONS[state.alertId] ?? []) : GLOBAL_SUGGESTIONS;

  return (
    <ArenaSheet
      open={state.open}
      placement={mobile ? 'bottom' : 'end'}
      title="Preguntar a Centinela"
      collapsed={collapsed}
      onCollapsedChange={setCollapsed}
      dismissible
      onClose={closeChat}
      footer={
        <form className="arena-stack arena-stack--group chat__footer" onSubmit={submit} onKeyDown={keys}>
          <ArenaTextarea
            id={FIELD_ID}
            label="Tu pregunta"
            rows={2}
            hint="Enter envía; Mayús + Enter, nueva línea"
            value={question}
            onChange={setQuestion}
          />
          <div className="arena-row chat__send">
            <ArenaButton type="submit" variant="secondary" icon="ph-bold ph-paper-plane-right" loading={answering} disabled={!question.trim()}>
              Preguntar
            </ArenaButton>
          </div>
        </form>
      }
    >
      <div className="arena-stack arena-stack--group chat">
        <div className="chat__context">
          {state.alertId ? (
            <ArenaTag removable onRemove={clearChatContext}>
              Sobre: {alertTitle ?? 'esta alerta'}
            </ArenaTag>
          ) : (
            <p className="text-muted">Pregunta sobre cualquier indicador vigilado.</p>
          )}
        </div>
        {entries.length === 0 ? (
          <div className="arena-stack arena-stack--group">
            <p className="text-muted">Respondo con los datos de la empresa, y cada cifra lleva su fuente. Por ejemplo:</p>
            <div className="arena-stack chat__suggestions">
              {suggestions.map((s) => (
                <ArenaButton key={s} variant="ghost" size="sm" icon="ph-bold ph-chat-circle-text" onClick={() => void ask(s)}>
                  {s}
                </ArenaButton>
              ))}
            </div>
          </div>
        ) : null}
        <ol ref={conversation} className="chat__conversation" role="log" aria-label="Conversación">
          {entries.map((e) => (
            <li key={e.id} className={e.role === 'user' ? 'bubble bubble--user' : 'bubble bubble--centinela'}>
              <span className="eyebrow">{e.role === 'user' ? 'Tú' : 'Centinela'}</span>
              {e.role === 'user' ? <p>{e.text}</p> : <Answer entry={e} />}
            </li>
          ))}
        </ol>
      </div>
    </ArenaSheet>
  );
}
