import type { RiskSignal } from '../../types/index.ts';
import { RISK_STYLES, TREND_META } from '../../theme/tokens.ts';
import { formatTimeAgo } from '../../utils/format.ts';

export function RiskPanel({ risk, delta }: { risk: RiskSignal; delta?: number }) {
  if (risk.level === 'unavailable' || risk.score === null) {
    return <div aria-label="ML risk unavailable">
      <p className="eyebrow">ML risk</p>
      <div className="mt-4 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.03] p-5">
        <p className="font-display font-extrabold text-lg">ML risk unavailable</p>
        <p className="text-sm text-slate-500 mt-1">No clinically validated model is configured for live observations.</p>
        <p className="text-xs text-slate-400 mt-3">No synthetic live risk score is generated. Historical replay research scoring, when present, is labelled separately.</p>
        {risk.disclaimer && <p className="text-xs text-slate-400 mt-2">{risk.disclaimer}</p>}
      </div>
    </div>;
  }
  const s=RISK_STYLES[risk.level], C=2*Math.PI*60, trend=TREND_META[risk.trend];
  const circumference=(risk.score/100)*C;
  return <div aria-label="Historical research risk signal">
    <p className="eyebrow">Historical replay · research risk</p>
    <div className="flex flex-wrap items-center gap-6 mt-4">
      <div className="relative h-36 w-36 shrink-0" role="img" aria-label={'Research risk '+risk.score+' of 100, level '+risk.level}>
        <svg viewBox="0 0 140 140" className="h-36 w-36 -rotate-90" aria-hidden>
          <circle cx="70" cy="70" r="60" fill="none" className="stroke-slate-100 dark:stroke-slate-800" strokeWidth="11" />
          <circle cx="70" cy="70" r="60" fill="none" strokeWidth="11" strokeLinecap="round" className={s.ring} strokeDasharray={circumference+' '+C} />
        </svg>
        <div className="absolute inset-0 grid place-items-center text-center"><div><p className={'metric text-[36px] leading-none '+s.text}>{risk.score}</p><p className="text-[11px] text-slate-400 font-semibold mt-0.5">/ 100</p></div></div>
      </div>
      <div className="min-w-0 flex-1">
        <p className={'font-display font-extrabold uppercase tracking-[0.14em] text-sm inline-flex items-center gap-2 '+s.text}><span className={'h-2 w-2 rounded-full '+s.dot} aria-hidden />{risk.level}</p>
        {risk.probability !== null && <p className="text-sm mt-2">Research-model probability <strong className="tabular-nums">{Math.round(risk.probability*100)}%</strong></p>}
        <p className={'text-xs font-bold mt-1 '+trend.cls}>{trend.arrow} {trend.label}{delta!==undefined&&delta!==0?' · '+(delta>0?'+':'')+delta+' in window':''}</p>
        <p className="text-[11px] text-slate-400 mt-1 tabular-nums">Updated {formatTimeAgo(risk.updatedAt)}</p>
        <p className="mt-2.5 inline-block text-[10px] font-bold tracking-[0.08em] px-2 py-1 rounded-md bg-slate-900/[0.04] text-slate-500 border border-slate-200/80 dark:bg-white/[0.06] dark:text-slate-300 dark:border-white/10">HISTORICAL REPLAY · RESEARCH ONLY</p>
      </div>
    </div>
  </div>;
}

export function News2Panel({ score, compact }: { score: number | null; compact?: boolean }) {
  if(score===null) return <div aria-label="NEWS2 clinical reference score"><p className="eyebrow">NEWS2 · Clinical reference</p><p className="text-sm text-slate-500 mt-3">Unavailable — complete clinical inputs were not supplied with this observation.</p></div>;
  const band=score>=7?'High':score>=5?'Medium':score>=1?'Low':'No alert';
  const cls=score>=7?'text-rose-600 dark:text-rose-400':score>=5?'text-orange-600 dark:text-orange-400':'text-teal-700 dark:text-teal-300';
  return <div aria-label="NEWS2 clinical reference score">
    <p className="eyebrow">NEWS2 · Clinical reference</p>
    <div className="flex items-baseline gap-2 mt-2"><p className={'metric leading-none '+(compact?'text-4xl':'text-5xl')+' '+cls}>{score}</p><span className="text-xs font-bold text-slate-400 uppercase tracking-wide">{band}</span></div>
    <div className="mt-3 flex gap-1.5" aria-hidden>{[0,1,2,3,4,5,6,7,8,9,10].map(i=><span key={i} className={'h-1.5 flex-1 rounded-full '+(i<score?(score>=7?'bg-rose-400':score>=5?'bg-orange-400':'bg-teal-400'):'bg-slate-100 dark:bg-white/10')}/>)}</div>
    <p className="text-xs text-slate-500 mt-3 leading-relaxed">Reference calculation only; verify against local policy. NEWS2 is separate from ML risk and does not imply model validation.</p>
  </div>;
}