'use client';

import { useState, type FormEvent } from 'react';
import { api } from '@/lib/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    try { await api('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }); location.href = '/dashboard'; }
    catch (e) { setError((e as Error).message); }
  }
  return <main className="flex min-h-screen items-center justify-center p-6"><form onSubmit={submit} className="card w-full max-w-sm space-y-5"><h1 className="text-2xl font-bold">Dashboard login</h1><label>Username<input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required /></label>{error && <p role="alert" className="text-red-400">{error}</p>}<button className="primary w-full">Sign in</button></form></main>;
}
