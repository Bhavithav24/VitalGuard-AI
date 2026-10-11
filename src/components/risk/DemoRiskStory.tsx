import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { SectionCard } from '../ui/Primitives.tsx';
import { useSimulation } from '../../store/useSimulation.ts';

export function DemoRiskStory({ patientId }: { patientId: string }) {
  const { latest, risks, histories } = useSimulation();
  const v = latest[patientId];
  const r = risks[patientId];
  const h = histories[patientId] ?? [];
  if (!v || !r) return null;

  const previous = h.length > 1 ? h[h.length - 2] : undefined;
  const changes = previous ? [
    { label: 'Heart rate', value: Math.round(v.heartRate - previous.heartRate), unit: 'bpm' },
    { label: 'SpO₂', value: Math.round(v.spo2 - previous.spo2), unit: 'pt' },
    { label: 'Respiratory rate', value: Math.round(v.respiratoryRate - previous.respiratoryRate), unit: '/min' },
  ].filter((x) => x.value !== 0) : [];

  const direction = r.trend === 'worsening' ? 'upward' : r.trend === 'recovering' ? 'downward' : 'stable';
  const DirectionIcon = direction === 'upward' ? ArrowUpRight : direction === 'downward' ? ArrowDownRight : Minus;

  return (
    <div className="mt-4">
      <SectionCard eyebrow="Demo narrative" title="What changed in this simulation?" hint="A compact, human-readable view of the synthetic signal" label="Synthetic risk story">
        <div className="rounded-2xl border border-teal-200/70 bg-teal-50/50 p-4 dark:border-teal-900/60 dark:bg-teal-950/20">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 rounded-xl bg-white p-2 text-teal-700 shadow-sm dark:bg-slate-900 dark:text-teal-300"><DirectionIcon size={17} aria-hidden /></span>
            <div>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100">The synthetic risk signal is {direction} at {r.score}/100.</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                This summary describes simulated data movement only. It is not a diagnosis, prediction of a real patient outcome, or clinical recommendation.
              </p>
            </div>
          </div>
          {changes.length > 0 ? (
            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              {changes.map((change) => (
                <div key={change.label} className="rounded-xl border border-slate-200 bg-white/80 px-3 py-2 dark:border-slate-800 dark:bg-slate-950/40">
                  <p className="text-[11px] font-semibold text-slate-500">{change.label}</p>
                  <p className={`mt-0.5 text-sm font-bold tabular-nums ${change.value > 0 ? 'text-slate-800 dark:text-slate-100' : 'text-teal-700 dark:text-teal-300'}`}>
                    {change.value > 0 ? '+' : ''}{change.value} {change.unit}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-xs text-slate-500">Start the simulation to see changes appear here.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
