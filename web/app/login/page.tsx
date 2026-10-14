'use client';

import { useState, type FormEvent } from 'react';
import { api } from '@/lib/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true);
    try { await api('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }); location.href = '/dashboard'; }
    catch (e) { setError((e as Error).message); setBusy(false); }
  }
  return <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_center,_rgb(30_41_59_/_0.32),_transparent_65%)] p-6"><form onSubmit={submit} className="card w-full max-w-sm space-y-5 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.05)]"><h1 className="text-3xl font-bold">Dashboard login</h1><label>Username<input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} disabled={busy} required /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} disabled={busy} required /></label>{error && <p role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p>}<button className="primary w-full py-3" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form></main>;
}
