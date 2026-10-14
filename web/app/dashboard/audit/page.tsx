'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Audit = { id: number; actor_id: string; action: string; target: string; details: Record<string, unknown>; created_at: string };

export default function AuditPage() {
  const [rows, setRows] = useState<Audit[]>([]);
  const [actor, setActor] = useState('');
  const [action, setAction] = useState('');
  const [error, setError] = useState('');
  async function load(actorFilter = '', actionFilter = '') {
    try { setRows(await api<Audit[]>(`/audit?actor=${encodeURIComponent(actorFilter)}&action=${encodeURIComponent(actionFilter)}`)); setError(''); }
    catch (cause) { setError((cause as Error).message); }
  }
  useEffect(() => { void load(); }, []);
  return <><h1 className="text-4xl font-bold">Audit log</h1>{error && <p role="alert">{error}</p>}
    <section className="card space-y-3"><div className="flex gap-2"><input placeholder="Actor" value={actor} onChange={e => setActor(e.target.value)} /><input placeholder="Action prefix" value={action} onChange={e => setAction(e.target.value)} /><button className="secondary" onClick={() => load(actor, action)}>Filter</button></div>
      {rows.length ? <ul className="space-y-2 text-sm">{rows.map(row => <li key={row.id}>#{row.id} {new Date(row.created_at).toLocaleString()} — {row.actor_id}: {row.action} {row.target}</li>)}</ul> : <p>No audit entries found.</p>}
    </section>
  </>;
}
