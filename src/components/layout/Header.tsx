import { useState } from 'react';
import { Bell, RefreshCw, LogOut } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useSimulation } from '../../store/useSimulation.ts';
import { formatTimeAgo } from '../../utils/format.ts';
import { useOptionalAuth } from '../../store/AuthContext.tsx';
import { useLiveEvents } from '../../services/useLiveEvents.ts';

export function Header({ title, subtitle }: { title: string; subtitle?: string }) {
  const { alerts, lastRefresh, refresh } = useSimulation();
  const auth = useOptionalAuth();
  const username = auth?.username ?? null;
  const role = auth?.role ?? null;
  const logout = auth?.logout ?? (() => {});
  const { status: streamStatus } = useLiveEvents();
  const open = alerts.filter((a) => a.status === 'open').length;
  const initials = (username || 'Operator')
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('') || 'OP';
  const [spinning, setSpinning] = useState(false);
  return (
    <header className="sticky top-0 z-20 bg-[#f5f8fb]/85 dark:bg-slate-950/80 backdrop-blur-xl border-b border-slate-200/70 dark:border-slate-800/80">
      <div className="flex items-center gap-3 px-4 md:px-8 h-[70px]">
        <div className="min-w-0">
          <h1 className="font-display font-extrabold text-[17px] md:text-lg tracking-tight truncate">{title}</h1>
          {subtitle && <p className="text-xs text-slate-500 truncate mt-0.5">{subtitle}</p>}
        </div>
        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <span className={`hidden sm:inline-flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1.5 rounded-full border ${streamStatus==='connected'?'border-emerald-200/80 bg-emerald-50/70 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200 dark:border-emerald-900/60':'border-amber-200/80 bg-amber-50/70 text-amber-800 dark:bg-amber-950/50 dark:text-amber-200 dark:border-amber-900/60'}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${streamStatus==='connected'?'bg-emerald-500':'bg-amber-500'}`} aria-hidden />
            {streamStatus==='connected'?'Stream connected':streamStatus==='reconnecting'?'Stream reconnecting':streamStatus==='connecting'?'Connecting stream':'Stream offline'}
          </span>
          <span className="hidden xl:inline text-[11px] text-slate-400 tabular-nums" title="Last data refresh">
            Updated {formatTimeAgo(lastRefresh)}
          </span>
          <button
            aria-label="Refresh backend data timestamps"
            title="Refresh backend data timestamps"
            onClick={() => { setSpinning(true); refresh(); window.setTimeout(() => setSpinning(false), 600); }}
            className="icon-btn"
          >
            <RefreshCw size={17} className={spinning ? 'animate-spin' : ''} aria-hidden />
          </button>
          <Link to="/alerts" aria-label={`Alert center, ${open} open alerts`} className="icon-btn relative">
            <Bell size={17} aria-hidden />
            {open > 0 && (
              <span className="absolute top-0.5 right-0.5 min-w-[18px] h-[18px] px-1 rounded-full text-white text-[10px] grid place-items-center font-bold tabular-nums" style={{ background: 'linear-gradient(135deg,#e11d48,#f43f5e)' }}>{open}</span>
            )}
          </Link>
          <span className="hidden md:grid place-items-center h-9 w-9 rounded-full text-white text-xs font-extrabold" style={{ background: 'linear-gradient(135deg,#0f766e,#0891b2)' }} aria-hidden>{initials}</span>
          <span className="hidden lg:inline max-w-28 truncate text-xs text-slate-500" title={username ?? "User"}>{username ?? "Operator"}</span>
          {role && <span className="hidden sm:inline-flex px-2 py-1 rounded-md bg-slate-100 dark:bg-white/10 text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300">{role}</span>}
          <button type="button" onClick={logout} aria-label="Sign out" title="Sign out" className="icon-btn"><LogOut size={17} aria-hidden /></button>
        </div>
      </div>
    </header>
  );
}
