'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, type GuildData } from '@/lib/api';
import { pages } from '@/lib/navigation';

type BotTask = { id: number; type: string; status: string; error: string | null };

export default function Dashboard() {
  const [guild, setGuild] = useState<GuildData | null>(null);
  const [tasks, setTasks] = useState<BotTask[]>([]);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState('');

  useEffect(() => {
    Promise.all([api<GuildData>('/guild/data'), api<BotTask[]>('/tasks')])
      .then(([data, recent]) => { setGuild(data); setTasks(recent); })
      .catch(cause => setError((cause as Error).message));
  }, []);

  async function refreshGuildData() {
    setRefreshing(true);
    setRefreshMessage('Sync queued.');
    try {
      const queued = await api<{ id: number }>('/tasks', {
        method: 'POST',
        body: JSON.stringify({ type: 'sync_guild_data', payload: {} }),
      });
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const recent = await api<BotTask[]>('/tasks');
        setTasks(recent);
        const task = recent.find(item => item.id === queued.id);
        if (task?.status === 'failed') throw new Error(task.error || 'Guild sync failed.');
        if (task?.status === 'done') {
          setGuild(await api<GuildData>('/guild/data'));
          setRefreshMessage('Guild data refreshed.');
          return;
        }
      }
      throw new Error('Guild sync is still pending. Check recent bot tasks.');
    } catch (cause) {
      setRefreshMessage((cause as Error).message);
    } finally {
      setRefreshing(false);
    }
  }

  return <>
    <div className="flex items-center justify-between">
      <div><h1 className="text-3xl font-bold">Overview</h1><p className="mt-2 text-slate-400">Configure your Discord bot from one place.</p></div>
      <button className="secondary" disabled={refreshing} onClick={refreshGuildData}>{refreshing ? 'Refreshing…' : 'Refresh guild data'}</button>
    </div>
    {refreshMessage && <p className="text-sm text-slate-400">{refreshMessage}</p>}
    {error && <p role="alert">{error}</p>}
    <div className="grid gap-4 md:grid-cols-3"><div className="card">Channels: {guild?.channels.length ?? '…'}</div><div className="card">Roles: {guild?.roles.length ?? '…'}</div><div className="card">Emojis: {guild?.emojis.length ?? '…'}</div></div>
    <div className="grid gap-4 md:grid-cols-2">{pages.slice(1).map(page => <Link className="card hover:border-indigo-500" href={page.href} key={page.href}>{page.label} →</Link>)}</div>
    <section className="card"><h2 className="mb-3 text-lg font-semibold">Recent bot tasks</h2>{tasks.length ? <ul className="space-y-2 text-sm">{tasks.slice(0, 10).map(task => <li key={task.id}>#{task.id} {task.type}: <span className={task.status === 'failed' ? 'text-red-400' : 'text-slate-300'}>{task.status}</span>{task.error && <span className="ml-2 text-red-400">{task.error}</span>}</li>)}</ul> : <p className="text-slate-400">No tasks yet.</p>}</section>
  </>;
}
