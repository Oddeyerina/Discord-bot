'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Health = { api: string; database: string; bot: string; bot_last_seen: string | null };

export default function HealthPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const refresh = () => { api<Health>('/health/detail').then(data => { setHealth(data); setError(''); }).catch(cause => setError((cause as Error).message)); };
    refresh();
    const timer = window.setInterval(refresh, 30000);
    return () => window.clearInterval(timer);
  }, []);
  return <><h1 className="text-4xl font-bold">Health</h1>{error && <p role="alert" className="text-red-300">{error}</p>}
    <section className="grid gap-4 md:grid-cols-3">
      {([['API', health?.api], ['Database', health?.database], ['Bot', health?.bot]] as const).map(([label, status]) =>
        <div className="card" key={label}><p className="text-sm text-slate-400">{label}</p><p className={`text-2xl font-semibold ${status === 'ok' || status === 'online' ? 'text-green-300' : 'text-red-300'}`}>{status || 'Checking…'}</p></div>)}
    </section>
    <p className="text-sm text-slate-400">Last bot heartbeat: {health?.bot_last_seen ? new Date(health.bot_last_seen).toLocaleString() : 'Unknown'}</p>
  </>;
}
