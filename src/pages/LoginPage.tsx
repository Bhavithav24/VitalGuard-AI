import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext.tsx';
export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState(''); const [password, setPassword] = useState('');
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const demoRoles = [
    { label: 'Admin', username: 'admin', password: 'VitalGuardAdmin@2026', icon: '🛡' },
    { label: 'Clinician', username: 'clinician', password: 'VitalGuardClinician@2026', icon: '♙' },
    { label: 'Nurse', username: 'nurse', password: 'VitalGuardNurse@2026', icon: '♡' },
  ];
  function fillDemo(username: string, password: string) { setUsername(username); setPassword(password); setError(''); }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true);
    try { await login(username.trim(), password); navigate('/dashboard', { replace: true }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to sign in.'); }
    finally { setBusy(false); }
  }
  return <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-4 py-10">
    <section className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
      <div className="mb-8"><p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-400">VitalGuard AI</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">Clinical Portal Login</h1>
        <p className="mt-2 text-sm leading-6 text-slate-400">Sign in to access the patient monitoring workspace. Access tokens expire after 15 minutes.</p></div>
      <form className="space-y-5" onSubmit={submit}>
        <div><label htmlFor="username" className="mb-2 block text-sm font-medium text-slate-300">Username</label>
          <input id="username" autoComplete="username" required maxLength={128} value={username} onChange={e => setUsername(e.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20" /></div>
        <div><label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-300">Password</label>
          <input id="password" type="password" autoComplete="current-password" required maxLength={1024} value={password} onChange={e => setPassword(e.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20" /></div>
        {error && <p role="alert" className="rounded-lg border border-rose-900 bg-rose-950/60 px-3 py-2 text-sm text-rose-200">{error}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60">{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <div className="mt-6 border-t border-slate-800 pt-5">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Demo role quick-fill</p>
        <div className="grid grid-cols-3 gap-2">
          {demoRoles.map(role => <button key={role.username} type="button" onClick={() => fillDemo(role.username, role.password)} className="rounded-lg border border-slate-800 bg-slate-950/70 px-2 py-3 text-xs font-semibold text-slate-300 transition hover:border-cyan-700 hover:bg-slate-900"><span className="block text-base">{role.icon}</span><span className="mt-1 block">{role.label}</span></button>)}
        </div>
      </div>
      <p className="mt-5 text-center text-xs leading-5 text-slate-500">Demo deployment. Not clinically validated and must not be used for real patient care.</p>
    </section></main>;
}
