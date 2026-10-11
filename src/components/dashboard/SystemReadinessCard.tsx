import { useEffect, useState } from 'react';
import { Activity, CheckCircle2, CircleAlert, RefreshCw, ServerCog } from 'lucide-react';
import { api, type ReadinessSnapshot } from '../../services/api.ts';

export function SystemReadinessCard() {
  const [state, setState] = useState<ReadinessSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setState(await api.readiness());
    } catch {
      setState(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const ready = state?.status === 'ready';
  const checks = state?.checks;

  return (
    <section className="card mt-4 overflow-hidden" aria-labelledby="system-readiness-title">
      <div className="flex flex-col gap-4 p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="eyebrow flex items-center gap-2"><ServerCog size={13} aria-hidden /> Platform readiness</p>
            <h2 id="system-readiness-title" className="mt-1 text-base font-bold text-slate-900 dark:text-slate-100">
              {loading ? 'Checking live services…' : ready ? 'Demo environment ready' : 'Demo environment needs attention'}
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Live checks for the API, synthetic model and demo data layer.
            </p>
          </div>
          <button className="btn-secondary !py-1.5 !text-xs" onClick={() => void load()} disabled={loading}>
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} aria-hidden /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            ['API', checks?.api === 'ok'],
            ['Database', checks?.database === 'ok'],
            ['Model', checks?.model_loaded],
            ['Auth', checks?.operator_auth_configured],
          ].map(([label, ok]) => (
            <div key={String(label)} className="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2 dark:border-slate-800 dark:bg-slate-950/50">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
                {ok ? <CheckCircle2 size={14} className="text-emerald-600" aria-hidden /> : <CircleAlert size={14} className="text-amber-600" aria-hidden />}
                {label}
              </div>
              <p className="mt-1 text-[11px] text-slate-400">{loading ? 'Checking…' : ok ? 'Operational' : 'Needs attention'}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-400">
          <span className="inline-flex items-center gap-1.5"><Activity size={12} aria-hidden /> Model {state?.model_version ?? '—'}</span>
          <span>Transport: {state?.checks.websocket_transport ?? '—'}</span>
          <span>Synthetic demo only · not clinically validated</span>
        </div>
      </div>
    </section>
  );
}
