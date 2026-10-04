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
import { ApiError, chat, getAlert, getQuery } from '../api/client';
import type { ChatMessage, ChatOutcome, Query } from '../api/types';
import { SentenceWithFigures } from '../common/SentenceWithFigures';
import { SeriesChart, sourceTitle } from '../common/SeriesChart';
import { useSimulation } from '../state/Simulation';

const FIELD_ID = 'chat-question';

const MAX_QUESTION = 500;

type Entry =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'centinela'; status: 'searching' | 'writing'; step: string; text: string; path: string[] }
  | { id: number; role: 'centinela'; status: 'ready'; message: ChatMessage; path: string[] }
  | { id: number; role: 'centinela'; status: 'error'; message: string };

const ALERT_SUGGESTIONS = ['¿Por qué se generó esta alerta?', '¿Qué propones hacer?', '¿Cuál es la causa?'];

const GLOBAL_SUGGESTIONS = [
  '¿Qué clientes tienen más saldo vencido hoy?',
  '¿Cómo va la cobertura de inventario?',
  '¿Cuál es la tasa de cambio del dólar hoy?',
];

const UNANSWERED: Record<Exclude<ChatOutcome, 'answered'>, { title: string; icon: string }> = {
  no_evidence: { title: 'Sin evidencia suficiente', icon: 'ph-bold ph-question' },
  out_of_scope: { title: 'Fuera de lo que respondo', icon: 'ph-bold ph-signpost' },
  refused: { title: 'Pregunta no procesada', icon: 'ph-bold ph-shield-warning' },
};

function Path({ steps }: { steps: string[] }) {
  if (steps.length === 0) {
    return null;
  }
  return (
    <div className="arena-stack chat__path">
      <span className="eyebrow">Camino en el árbol de decisión</span>
      <ol className="text-muted">
        {steps.map((step, index) => (
          <li key={index}>{step}</li>
        ))}
      </ol>
    </div>
  );
}

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
        {entry.message}
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
  const { message, path } = entry;
  const outcome = message.outcome === 'answered' && !message.enoughEvidence ? 'no_evidence' : message.outcome;
  if (outcome !== 'answered') {
    const { title, icon } = UNANSWERED[outcome];
    return (
      <div className="arena-stack arena-stack--group">
        <ArenaAlert tone="info" icon={icon} title={title}>
          <SentenceWithFigures text={message.text} figures={message.figures} />
        </ArenaAlert>
        <Path steps={path} />
      </div>
    );
  }
  return (
    <div className="arena-stack arena-stack--group">
      <p>
        <SentenceWithFigures text={message.text} figures={message.figures} />
      </p>
      <MessageChart message={message} />
      <Path steps={path} />
    </div>
  );
}

export function Chat() {
  const mobile = useArenaViewportBelow('lg');
  const { chat: state, closeChat, clearChatContext, changed } = useSimulation();
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
      { id: answerId, role: 'centinela', status: 'searching', step: 'Buscando la respuesta', text: '', path: [] },
    ]);
    try {
      for await (const event of chat({ question: clean, ...(state.alertId ? { alertId: state.alertId } : {}) })) {
        if (event.event === 'step') {
          const step = event.data.description;
          const walked = event.data.node ? [step] : [];
          update(answerId, (e) =>
            e.role === 'centinela' && e.status === 'searching' ? { ...e, step, path: [...e.path, ...walked] } : e,
          );
        } else {
          const message = event.data;
          changed();
          update(answerId, (e) => ({
            id: answerId,
            role: 'centinela',
            status: 'ready',
            message,
            path: e.role === 'centinela' && e.status !== 'error' ? e.path : [],
          }));
        }
      }
    } catch (e: unknown) {
      const message = e instanceof ApiError ? e.message : 'Intenta de nuevo en unos segundos.';
      update(answerId, () => ({ id: answerId, role: 'centinela', status: 'error', message }));
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

  const suggestions = state.alertId ? ALERT_SUGGESTIONS : GLOBAL_SUGGESTIONS;

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
            maxLength={MAX_QUESTION}
            counter
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
            <p className="text-muted">
              Respondo con los datos de la empresa y cada cifra lleva su fuente. No apruebo ni ejecuto: eso se decide en la bandeja. Por ejemplo:
            </p>
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
