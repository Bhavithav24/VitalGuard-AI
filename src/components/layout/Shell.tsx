import type { ReactNode } from 'react';
import { Sidebar, MobileNav } from './Sidebar.tsx';
import { Header } from './Header.tsx';
import { Toasts } from './Toasts.tsx';
import { useLiveEvents } from '../../services/useLiveEvents.ts';

export function Shell({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  const { status, patientCount } = useLiveEvents();
  const live = status === 'connected';
  return (
    <div className="flex flex-col lg:flex-row min-h-screen bg-[#f5f8fb] dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:px-3 focus:py-2 focus:bg-white focus:rounded-lg focus:text-sm focus:font-bold">
        Skip to main content
      </a>
      <MobileNav />
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col min-h-screen">
        <Header title={title} subtitle={subtitle} />
        <div className="px-4 md:px-8 pt-3 max-w-[1440px] w-full mx-auto">
          <div className={`flex flex-wrap items-center gap-2 rounded-2xl border px-4 py-2.5 text-xs shadow-[0_8px_24px_-20px_rgba(15,118,110,.55)] ${live ? 'border-teal-200 bg-teal-50 text-teal-800 dark:border-teal-900 dark:bg-teal-950/40 dark:text-teal-200' : 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'}`} role="status" aria-live="polite">
            <span className={`h-2 w-2 rounded-full ${live ? 'bg-teal-500 pulse-dot' : 'bg-amber-500'}`} aria-hidden />
            <strong>Backend live channel: {status}</strong>
            <span className="opacity-80">· {patientCount} patients reporting live in this view</span>
            <span className="ml-auto inline-flex items-center gap-2 text-[10px] uppercase tracking-wider font-bold"><span className="hidden sm:inline opacity-60">Source</span><span className="rounded-md border border-current/20 px-1.5 py-0.5">Controlled demo telemetry</span></span>
          </div>
        </div>
        <main id="main-content" className="page-enter flex-1 px-4 md:px-8 py-6 max-w-[1440px] w-full mx-auto" tabIndex={-1}>
          {children}
        </main>
        <footer className="px-6 md:px-8 pb-6 flex flex-wrap items-center gap-2 text-[11px] text-slate-400 dark:text-slate-500">
          <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />VitalGuard AI · clinical intelligence prototype</span>
          <span aria-hidden className="opacity-50">·</span>
          <span>Observations are accepted only from authorized backend sources; the deployed demo uses a controlled bedside-monitor telemetry source.</span>
        </footer>
      </div>
      <Toasts />
    </div>
  );
}
