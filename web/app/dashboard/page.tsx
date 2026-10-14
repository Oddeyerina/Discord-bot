'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { pages } from '@/lib/navigation';

type Ticket = { id: number; guild_id: string; thread_id: string; user_id: string; reason: string; status: string };
type Task = { id: number; type: string; status: string; error: string | null };
type Audit = { id: number; actor_id: string; action: string; target: string };
type Warning = { id: number; user_id: string; reason: string };
type Summary = {
  tiles: { members_online: number | null; in_voice: number | null; total_members: number | null;
           open_tickets: number; tickets_7d: number; bot_status: 'online' | 'offline' };
  chart: { date: string; opened: number }[];
  recent_tickets: Ticket[];
  recent_tasks: Task[];
  recent_audit: Audit[];
  recent_warnings: Warning[];
  sections: { audit: boolean; warnings: boolean };
};

const tileValue = (value: number | null) => value === null ? '–' : value.toLocaleString();
const badge = (status: string) => status === 'done' || status === 'closed'
  ? 'bg-green-500/15 text-green-300' : status === 'failed'
    ? 'bg-red-500/15 text-red-300' : 'bg-amber-500/15 text-amber-300';

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState('');

  useEffect(() => {
    const refresh = () => { api<Summary>('/dashboard/summary').then(data => { setSummary(data); setError(''); })
      .catch(cause => setError((cause as Error).message)); };
    refresh();
    const timer = window.setInterval(refresh, 30000);
    return () => window.clearInterval(timer);
  }, []);

  async function refreshGuildData() {
    setRefreshing(true); setRefreshMessage('Sync queued.');
    try {
      const queued = await api<{ id: number }>('/tasks', {
        method: 'POST', body: JSON.stringify({ type: 'sync_guild_data', payload: {} }),
      });
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const tasks = await api<Task[]>('/tasks');
        const task = tasks.find(item => item.id === queued.id);
        if (task?.status === 'failed') throw new Error(task.error || 'Guild sync failed.');
        if (task?.status === 'done') {
          setSummary(await api<Summary>('/dashboard/summary'));
          setRefreshMessage('Guild data refreshed.');
          return;
        }
      }
      throw new Error('Guild sync is still pending. Check recent bot tasks.');
    } catch (cause) { setRefreshMessage((cause as Error).message); }
    finally { setRefreshing(false); }
  }

  const chartMax = Math.max(0, ...(summary?.chart.map(day => day.opened) || []));
  return <>
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div><h1 className="text-4xl font-bold">Overview</h1><p className="mt-2 text-slate-400">Server activity at a glance.</p></div>
      <button type="button" className="secondary" disabled={refreshing} onClick={refreshGuildData}>{refreshing ? 'Refreshing…' : 'Refresh guild data'}</button>
    </div>
    {refreshMessage && <p className="text-sm text-slate-400">{refreshMessage}</p>}
    {error && <p role="alert" className="text-red-300">{error}</p>}

    <section aria-label="Live metrics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {([
        ['Members online', summary?.tiles.members_online ?? null],
        ['In voice', summary?.tiles.in_voice ?? null],
        ['Total members', summary?.tiles.total_members ?? null],
        ['Open tickets', summary?.tiles.open_tickets ?? null],
        ['Tickets closed last 7 days', summary?.tiles.tickets_7d ?? null],
      ] as const).map(([label, value]) =>
        <div className="card" key={label}><p className="text-3xl font-semibold tabular-nums text-slate-100">{tileValue(value)}</p><p className="mt-1 text-sm text-slate-400">{label}</p></div>)}
      <div className="card"><p className={`text-3xl font-semibold ${summary?.tiles.bot_status === 'online' ? 'text-green-300' : 'text-red-300'}`}>{summary?.tiles.bot_status === 'online' ? 'Online' : summary ? 'Offline' : '–'}</p><p className="mt-1 text-sm text-slate-400">Bot status</p></div>
    </section>

    <section className="card" aria-label="Ticket activity chart"><h2 className="text-xl font-semibold">Tickets opened in the last 7 days</h2>
      {chartMax === 0 ? <p className="mt-6 text-slate-400">No activity yet</p> :
        <div className="mt-6 grid grid-cols-7 gap-2 sm:gap-4">
          {summary?.chart.map(day => <div className="flex min-w-0 flex-col items-center gap-1" key={day.date}>
            <span className="text-sm tabular-nums">{day.opened}</span>
            <div className="flex h-40 w-full max-w-16 items-end" aria-label={`${day.date}: ${day.opened} tickets`}>
              <div className="w-full rounded-t-md bg-indigo-400/80" style={{ height: `${Math.max(day.opened ? 8 : 2, day.opened / chartMax * 100)}%` }} />
            </div>
            <span className="text-xs text-slate-400" title={day.date}>{new Date(`${day.date}T00:00:00Z`).toLocaleDateString('en', { weekday: 'short', timeZone: 'UTC' })}</span>
          </div>)}
        </div>}
    </section>

    <section className="grid gap-4 lg:grid-cols-2" aria-label="Recent activity">
      <div className="card"><h2 className="mb-4 text-xl font-semibold">Recent tickets</h2>
        {summary?.recent_tickets.length ? <ul className="space-y-3 text-sm">{summary.recent_tickets.map(ticket =>
          <li className="border-b border-slate-800 pb-2 last:border-0" key={ticket.id}>
            <a className="text-indigo-300 hover:underline" href={`https://discord.com/channels/${ticket.guild_id}/${ticket.thread_id}`} target="_blank" rel="noreferrer">Ticket #{ticket.id}</a>
            <span className={`ml-2 rounded px-2 py-0.5 text-xs ${badge(ticket.status)}`}>{ticket.status}</span>
            <p className="mt-1">Opened by {ticket.user_id} · {ticket.reason}</p>
          </li>)}</ul> : <p className="text-sm text-slate-400">No tickets yet.</p>}
      </div>
      <div className="card"><h2 className="mb-4 text-xl font-semibold">Recent bot tasks</h2>
        {summary?.recent_tasks.length ? <ul className="space-y-3 text-sm">{summary.recent_tasks.map(task =>
          <li key={task.id}>#{task.id} {task.type}<span className={`ml-2 rounded px-2 py-0.5 text-xs ${badge(task.status)}`}>{task.status}</span>{task.error && <p className="text-red-300">{task.error}</p>}</li>)}</ul> : <p className="text-sm text-slate-400">No tasks yet.</p>}
      </div>
      {summary?.sections.audit && <div className="card"><h2 className="mb-4 text-xl font-semibold">Recent dashboard changes</h2>
        {summary.recent_audit.length ? <ul className="space-y-2 text-sm">{summary.recent_audit.map(row => <li key={row.id}>{row.actor_id}: {row.action} {row.target}</li>)}</ul> : <p className="text-sm text-slate-400">No changes yet.</p>}
      </div>}
      {summary?.sections.warnings && <div className="card"><h2 className="mb-4 text-xl font-semibold">Recent warnings</h2>
        {summary.recent_warnings.length ? <ul className="space-y-2 text-sm">{summary.recent_warnings.map(row => <li key={row.id}>User {row.user_id}: {row.reason}</li>)}</ul> : <p className="text-sm text-slate-400">No warnings yet.</p>}
      </div>}
    </section>

    <section><h2 className="mb-4 text-xl font-semibold">Quick links</h2><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{pages.slice(1).map(page =>
      <Link className="card hover:border-indigo-500" href={page.href} key={page.href}>{page.label}</Link>)}</div></section>
  </>;
}
