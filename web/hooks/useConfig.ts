'use client';

import { useEffect, useState } from 'react';
import { api, type GuildData } from '@/lib/api';

export function useConfig<T extends object>(path: string, defaults: T) {
  const [value, setValue] = useState<T>(defaults);
  const [guild, setGuild] = useState<GuildData>({ channels: [], roles: [], emojis: [] });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    Promise.all([api<T>(path), api<GuildData>('/guild/data')])
      .then(([config, data]) => { setValue({ ...defaults, ...config }); setGuild(data); })
      .catch(e => setError(e.message));
  }, [path]);
  async function save() {
    setBusy(true); setError(''); setMessage('');
    try { await api(path, { method: 'PUT', body: JSON.stringify(value) }); setMessage('Saved.'); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function publish(kind: string) {
    setBusy(true); setError(''); setMessage('');
    try {
      await api(path, { method: 'PUT', body: JSON.stringify(value) });
      const result = await api<{ task_id: number }>(`/panels/${kind}/publish`, { method: 'POST' });
      setMessage(`Panel task #${result.task_id} queued.`);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return { value, setValue, guild, message, error, busy, save, publish };
}
