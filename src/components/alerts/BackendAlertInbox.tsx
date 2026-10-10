import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, RefreshCw, ShieldAlert, WifiOff } from 'lucide-react';
import { APP_CONFIG } from '../../services/config.ts';
import { useLiveEvents } from '../../services/useLiveEvents.ts';

type BackendAlert = {
  id: number;
  patient_id: string;
  severity: string;
  status: 'open' | 'acknowledged' | 'resolved';
  title: string;
  created_at: string;
  acknowledged_by?: string | null;
  details: Record<string, unknown>;
};
type AlertResponse = { items: BackendAlert[]; count: number; demo_only: true };

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${APP_CONFIG.apiBaseUrl}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new Error(`Alert API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export function BackendAlertInbox() {
  const { lastEvent, status } = useLiveEvents();
  const [items, setItems] = useState<BackendAlert[]>([]);
  const [filter, setFilter] = useState<'all' | BackendAlert['status']>('all');
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiRequest<AlertResponse>('/api/v1/alerts?limit=100');
      setItems(result.items);
      setError('');
    } catch {
      setError('Backend alert service is unavailable. Check the API deployment and database health.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load, lastEvent]);

  const transition = async (id: number, action: 'acknowledge' | 'resolve') => {
    setBusyId(id);
    try {
      await apiRequest(`/api/v1/alerts/${id}/${action}`, {
        method: 'POST',
        body: JSON.stringify({ actor: 'demo-operator' }),
      });
      await load();
    } catch {
      setError('Could not update this alert. Refresh and try again.');
    } finally {
      setBusyId(null);
    }
  };

  const filtered = items.filter((item) => filter === 'all' || item.status === filter);
  const count = (status: BackendAlert['status']) => items.filter((item) => item.status === status).length;

  return (
    <section className="card mt-5 p-4 sm:p-5" aria-labelledby="backend-alert-inbox">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow flex items-center gap-1.5"><ShieldAlert size={13} /> Persistent backend alerts</p>
          <h2 id="backend-alert-inbox" className="font-display text-xl font-extrabold mt-1">Alert operations inbox</h2>
          <p className="text-xs text-slate-500 mt-1">Synthetic backend alerts · demo operator identity only</p>
        </div>
        <button className="btn-secondary" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded-lg bg-rose-50 text-rose-700 px-2.5 py-1.5 dark:bg-rose-950/50 dark:text-rose-300">Open {count('open')}</span>
        <span className="rounded-lg bg-amber-50 text-amber-700 px-2.5 py-1.5 dark:bg-amber-950/50 dark:text-amber-300">Acknowledged {count('acknowledged')}</span>
        <span className="rounded-lg bg-teal-50 text-teal-700 px-2.5 py-1.5 dark:bg-teal-950/50 dark:text-teal-300">Resolved {count('resolved')}</span>
        <span className="inline-flex items-center gap-1 text-slate-400 ml-auto">
          {status === 'connected' ? <CheckCircle2 size={13} /> : <WifiOff size={13} />}
          Live channel: {status}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Backend alert filters">
        {(['all', 'open', 'acknowledged', 'resolved'] as const).map((value) => (
          <button key={value} className={`tab-btn ${filter === value ? 'tab-on' : 'tab-off'}`} onClick={() => setFilter(value)}>
            {value === 'all' ? 'All' : value[0].toUpperCase() + value.slice(1)}
          </button>
        ))}
      </div>
      {error && <p role="alert" className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:border-rose-900 dark:text-rose-200">{error}</p>}
      {loading && items.length === 0 ? <p className="text-sm text-slate-500 mt-4">Loading persistent alerts…</p> :
        filtered.length === 0 ? <p className="text-sm text-slate-500 mt-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 p-4">No backend alerts in this filter. Submit a synthetic prediction with an elevated score to create a demo alert.</p> :
        <div className="mt-3 space-y-2">
          {filtered.map((alert) => (
            <article key={alert.id} className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 flex flex-col sm:flex-row sm:items-center gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400">#{alert.id} · {alert.severity}</span>
                  <span className={`text-[10px] uppercase tracking-wider font-bold rounded-md px-2 py-1 ${alert.status === 'open' ? 'bg-rose-50 text-rose-700' : alert.status === 'acknowledged' ? 'bg-amber-50 text-amber-700' : 'bg-teal-50 text-teal-700'}`}>{alert.status}</span>
                </div>
                <p className="font-bold text-sm mt-1">{alert.title}</p>
                <p className="text-xs text-slate-500 mt-1">Patient {alert.patient_id} · {new Date(alert.created_at).toLocaleString()}</p>
              </div>
              <div className="flex gap-2">
                {alert.status === 'open' && <button className="btn-secondary !text-xs" disabled={busyId === alert.id} onClick={() => void transition(alert.id, 'acknowledge')}>Acknowledge</button>}
                {alert.status !== 'resolved' && <button className="btn-primary !text-xs" disabled={busyId === alert.id} onClick={() => void transition(alert.id, 'resolve')}>Resolve</button>}
              </div>
            </article>
          ))}
        </div>
      }
      <p className="text-[11px] text-slate-400 mt-3">For demonstration only. This inbox does not authenticate staff or provide clinical alarm monitoring.</p>
    </section>
  );
}
