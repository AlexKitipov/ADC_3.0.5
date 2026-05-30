import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, PauseCircle, PlayCircle, RefreshCw, Radio, ShieldCheck } from 'lucide-react';
import { sessionsAPI } from '../api/sessions';
import type { SessionEvent, TradingSessionState } from '../types';

interface SessionControlsProps {
  compact?: boolean;
}

export function SessionControls({ compact = false }: SessionControlsProps) {
  const [session, setSession] = useState<TradingSessionState | null>(null);
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSession = useCallback(async () => {
    try {
      setError(null);
      const response = await sessionsAPI.getCurrent();
      setSession(response.data);
      const eventsResponse = await sessionsAPI.getEvents(response.data.id, compact ? 3 : 25);
      setEvents(eventsResponse.data);
    } catch (fetchError: unknown) {
      const status = getHttpStatus(fetchError);
      if (status === 404) {
        setSession(null);
        setEvents([]);
        return;
      }
      console.error('Failed to load trading session:', fetchError);
      setError('Trading session status is unavailable.');
    } finally {
      setIsLoading(false);
    }
  }, [compact]);

  useEffect(() => {
    void loadSession();
    if (compact) {
      return undefined;
    }
    const interval = window.setInterval(() => void loadSession(), 5000);
    return () => window.clearInterval(interval);
  }, [compact, loadSession]);

  const createSession = async (autoStart = false) => {
    setIsMutating(true);
    try {
      setError(null);
      const response = await sessionsAPI.createSession({ auto_start: autoStart });
      setSession(response.data);
      const eventsResponse = await sessionsAPI.getEvents(response.data.id, compact ? 3 : 25);
      setEvents(eventsResponse.data);
    } catch (mutationError) {
      console.error('Failed to create trading session:', mutationError);
      setError('Unable to create a trading session.');
    } finally {
      setIsMutating(false);
    }
  };

  const changeSessionState = async (action: 'start' | 'stop') => {
    if (!session) {
      return;
    }
    setIsMutating(true);
    try {
      setError(null);
      const response = action === 'start'
        ? await sessionsAPI.startSession(session.id)
        : await sessionsAPI.stopSession(session.id);
      setSession(response.data);
      const eventsResponse = await sessionsAPI.getEvents(response.data.id, compact ? 3 : 25);
      setEvents(eventsResponse.data);
    } catch (mutationError) {
      console.error(`Failed to ${action} trading session:`, mutationError);
      setError(`Unable to ${action} the trading session.`);
    } finally {
      setIsMutating(false);
    }
  };

  const isRunning = session?.status === 'running';
  const shellClasses = compact
    ? 'rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-4'
    : 'rounded-2xl border border-slate-800 bg-slate-900/60 p-6';

  return (
    <section className={shellClasses} aria-label="Trading session controls">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className={`rounded-2xl p-2 ${isRunning ? 'bg-emerald-400/20 text-emerald-200' : 'bg-slate-800 text-slate-300'}`}>
            {isRunning ? <Radio size={compact ? 18 : 22} /> : <ShieldCheck size={compact ? 18 : 22} />}
          </span>
          <div>
            <p className="text-sm font-semibold text-white">
              {isLoading ? 'Loading session...' : session ? `Session ${session.status}` : 'No active session'}
            </p>
            <p className={compact ? 'text-xs text-emerald-100/80' : 'mt-1 text-sm text-slate-400'}>
              {session ? `${session.symbol} · ${session.open_positions} open positions · ${session.event_count} events` : 'Create a runtime session to control automated trading.'}
            </p>
          </div>
        </div>
        {!compact && (
          <button
            type="button"
            onClick={() => void loadSession()}
            className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800"
            aria-label="Refresh session"
          >
            <RefreshCw size={16} />
          </button>
        )}
      </div>

      {error && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-100">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {!compact && (
        <div className="mt-5 flex flex-wrap gap-3">
          {!session ? (
            <>
              <ActionButton disabled={isMutating} onClick={() => void createSession(false)} icon={<ShieldCheck size={16} />}>
                Create Session
              </ActionButton>
              <ActionButton disabled={isMutating} onClick={() => void createSession(true)} icon={<PlayCircle size={16} />}>
                Create & Start
              </ActionButton>
            </>
          ) : (
            <>
              <ActionButton disabled={isMutating || isRunning} onClick={() => void changeSessionState('start')} icon={<PlayCircle size={16} />}>
                Start
              </ActionButton>
              <ActionButton disabled={isMutating || !isRunning} onClick={() => void changeSessionState('stop')} icon={<PauseCircle size={16} />}>
                Stop
              </ActionButton>
            </>
          )}
        </div>
      )}

      {!compact && (
        <div className="mt-6">
          <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Session events</h4>
          <div className="mt-3 max-h-64 space-y-3 overflow-y-auto pr-2">
            {events.length > 0 ? events.map((event) => (
              <div key={`${event.timestamp}-${event.type}`} className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-white">{event.message}</p>
                  <time className="shrink-0 text-xs text-slate-500">{new Date(event.timestamp).toLocaleTimeString()}</time>
                </div>
                <p className="mt-1 text-xs uppercase tracking-[0.2em] text-brand-300">{event.type}</p>
              </div>
            )) : (
              <div className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
                Session events will appear here after a session starts.
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

interface ActionButtonProps {
  children: string;
  disabled: boolean;
  icon: JSX.Element;
  onClick: () => void;
}

function ActionButton({ children, disabled, icon, onClick }: ActionButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-lg border border-brand-500/40 bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:border-slate-700 disabled:bg-slate-800 disabled:text-slate-500"
    >
      {icon}
      {children}
    </button>
  );
}

function getHttpStatus(error: unknown): number | undefined {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { status?: number } }).response;
    return response?.status;
  }
  return undefined;
}
