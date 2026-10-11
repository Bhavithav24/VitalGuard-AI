import { useState } from 'react';
import { Activity, Pause, Play, RotateCcw, Zap } from 'lucide-react';
import { useSimulation } from '../../store/useSimulation.ts';

type Scenario = 'snapshot' | 'monitor' | 'rapid';

const SCENARIOS: Array<{ id: Scenario; title: string; description: string }> = [
  { id: 'snapshot', title: 'Clean snapshot', description: 'Reset the synthetic cohort and pause on a stable starting point.' },
  { id: 'monitor', title: 'Live monitoring', description: 'Run the normal simulation so risk signals evolve over time.' },
  { id: 'rapid', title: 'Rapid escalation', description: 'Run the demo at 2× speed to make changing signals visible quickly.' },
];

export function DemoScenarioLauncher() {
  const { running, speed, multiplier, start, pause, reset, setSpeed, setMultiplier } = useSimulation();
  const [selected, setSelected] = useState<Scenario>('snapshot');

  const launch = (id: Scenario) => {
    setSelected(id);
    reset();
    if (id === 'snapshot') {
      setSpeed('normal');
      setMultiplier(1);
      pause();
      return;
    }
    if (id === 'rapid') {
      setSpeed('fast');
      setMultiplier(2);
      start();
      return;
    }
    setSpeed('normal');
    setMultiplier(1);
    start();
  };

  return (
    <section className="card mt-4 overflow-hidden" aria-labelledby="demo-scenario-title">
      <div className="p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="eyebrow flex items-center gap-2"><Zap size={13} aria-hidden /> Demo controls</p>
            <h2 id="demo-scenario-title" className="mt-1 text-base font-bold text-slate-900 dark:text-slate-100">One-click scenario launcher</h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Prepare a repeatable synthetic story for a live presentation without changing patient data.</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-900 dark:text-slate-300">
            <Activity size={12} aria-hidden /> {running ? 'Monitoring live' : 'Simulation paused'} · {speed} · {multiplier}×
          </div>
        </div>

        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {SCENARIOS.map((scenario) => (
            <button
              key={scenario.id}
              type="button"
              onClick={() => launch(scenario.id)}
              className={`rounded-xl border px-3 py-3 text-left transition hover:-translate-y-0.5 hover:shadow-sm ${selected === scenario.id ? 'border-teal-400 bg-teal-50/70 dark:border-teal-700 dark:bg-teal-950/30' : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950/30'}`}
              aria-pressed={selected === scenario.id}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">{scenario.title}</span>
                {scenario.id === 'snapshot' ? <RotateCcw size={13} aria-hidden /> : scenario.id === 'rapid' ? <Zap size={13} aria-hidden /> : <Play size={13} aria-hidden />}
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">{scenario.description}</p>
            </button>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button type="button" className="btn-secondary !py-1.5 !text-xs" onClick={() => (running ? pause() : start())}>
            {running ? <Pause size={13} aria-hidden /> : <Play size={13} aria-hidden />}
            {running ? 'Pause simulation' : 'Resume simulation'}
          </button>
          <button type="button" className="btn-ghost !py-1.5 !text-xs" onClick={() => launch('snapshot')}>
            <RotateCcw size={13} aria-hidden /> Reset demo
          </button>
        </div>

        <p className="mt-3 text-[10px] text-slate-400">Synthetic demonstration only. Scenario controls change simulation timing, not clinical recommendations.</p>
      </div>
    </section>
  );
}
