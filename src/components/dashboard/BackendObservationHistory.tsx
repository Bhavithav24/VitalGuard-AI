import { useCallback, useEffect, useMemo, useState } from 'react';
import { Clock3, RefreshCw, History } from 'lucide-react';
import { APP_CONFIG } from '../../services/config.ts';
import { authorizedFetch } from '../../services/authenticatedFetch.ts';
import { useSimulation } from '../../store/useSimulation.ts';

type RecordItem = {
  id: number;
  patient_id: string;
  created_at: string;
  observed_at?: string | null;
  model_version: string;
  source_mode?: string | null;
  source_system?: string | null;
  prediction: { risk_score: number | null; risk_level: string; model_version: string; ml_available?: boolean };
};
type HistoryResponse = { items: RecordItem[]; count: number; limit: number; next_before_id: number | null; demo_only: true; disclaimer: string };

export function BackendObservationHistory() {
  const { patients } = useSimulation();
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [patientId, setPatientId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const patientIds = useMemo(() => new Set(patients.map((patient) => patient.id)), [patients]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: '25' });
      if (patientId.trim()) params.set('patient_id', patientId.trim());
      const response = await authorizedFetch(`${APP_CONFIG.apiBaseUrl}/api/v1/observations?${params.toString()}`, { signal: AbortSignal.timeout(8000) });
      if (!response.ok) throw new Error('History API unavailable');
      setData(await response.json() as HistoryResponse);
      setError('');
    } catch {
      setError('Backend observation history is unavailable. Check the API deployment and storage health.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => { void load(); }, [load]);

  const items = data?.items.filter((item) => patientIds.has(item.patient_id)) ?? [];

  return (
    <section className="card mt-4 p-4 sm:p-5" aria-labelledby="backend-history-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow flex items-center gap-1.5"><History size={13} /> Persisted backend records</p>
          <h2 id="backend-history-heading" className="font-display text-xl font-extrabold mt-1">Observation history</h2>
          <p className="text-xs text-slate-500 mt-1">Backend-persisted observations · newest first</p>
        </div>
        <button className="btn-secondary" onClick={() => void load()} disabled={loading}><RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh</button>
      </div>
      <form className="mt-3 flex flex-wrap gap-2" onSubmit={(event) => { event.preventDefault(); void load(); }}>
        <input className="input-field min-w-[200px] flex-1" aria-label="Filter history by patient ID" placeholder="Filter by patient ID" value={patientId} onChange={(event) => setPatientId(event.target.value)} maxLength={64} />
        <button className="btn-secondary" type="submit">Apply filter</button>
        {patientId && <button className="btn-ghost" type="button" onClick={() => setPatientId('')}>Clear</button>}
      </form>
      {error && <p role="alert" className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/40 dark:border-amber-900 dark:text-amber-200">{error}</p>}
      {data && <>
        <p className="text-xs text-slate-500 mt-3">{items.length} current-patient record(s) shown · {data.count} returned from backend</p>
        {items.length ? <div className="overflow-x-auto mt-2">
          <table className="w-full text-sm">
            <thead><tr className="table-head"><th>Record</th><th>Patient</th><th>Risk</th><th>Source</th><th>Observed at</th></tr></thead>
            <tbody>{items.map((item) => <tr key={item.id} className="table-row">
              <td className="px-3 py-3 text-slate-500">#{item.id}</td>
              <td className="px-3 py-3 font-semibold">{item.patient_id}</td>
              <td className="px-3 py-3 font-bold tabular-nums">{item.prediction.risk_score === null || item.prediction.risk_score === undefined ? 'ML unavailable' : `${item.prediction.risk_score}/100`}</td>
              <td className="px-3 py-3 text-xs text-slate-500">{item.source_system || 'authorized backend'}{item.source_mode === 'historical_replay' ? ' · replay' : ''}</td>
              <td className="px-3 py-3 text-xs text-slate-500 whitespace-nowrap"><Clock3 size={12} className="inline mr-1" />{new Date(item.observed_at || item.created_at).toLocaleString()}</td>
            </tr>)}</tbody>
          </table>
        </div> : <p className="text-sm text-slate-500 mt-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 p-4">No current-patient observations are persisted yet.</p>}
      </>}
      <p className="mt-3 text-[11px] text-slate-400">Only records belonging to the current patient census are shown here. Research-only model results are never presented as clinical risk.</p>
    </section>
  );
}
