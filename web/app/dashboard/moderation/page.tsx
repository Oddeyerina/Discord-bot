'use client';

import { useEffect, useState } from 'react';
import ChannelSelect from '@/components/ChannelSelect';
import Status from '@/components/Status';
import { api, type GuildData } from '@/lib/api';

type Config = { warn_kick_threshold: number; warn_ban_threshold: number; log_channel_id: string; dm_on_warn: boolean };
type Warning = { id: number; user_id: string; moderator_id: string; reason: string; created_at: string };
const defaults: Config = { warn_kick_threshold: 3, warn_ban_threshold: 5, log_channel_id: '', dm_on_warn: true };

export default function ModerationPage() {
  const [value, setValue] = useState<Config>(defaults);
  const [guild, setGuild] = useState<GuildData>({ channels: [], roles: [], emojis: [] });
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [userId, setUserId] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    Promise.all([api<Config>('/moderation/config'), api<GuildData>('/guild/data'), api<Warning[]>('/moderation/warnings')])
      .then(([config, data, rows]) => { setValue({ ...defaults, ...config }); setGuild(data); setWarnings(rows); })
      .catch(cause => setError((cause as Error).message));
  }, []);
  async function save() {
    setError(''); setMessage('');
    try { setValue(await api<Config>('/moderation/config', { method: 'PUT', body: JSON.stringify(value) })); setMessage('Settings saved.'); }
    catch (cause) { setError((cause as Error).message); }
  }
  async function search() {
    try { setWarnings(await api<Warning[]>(`/moderation/warnings?user_id=${encodeURIComponent(userId)}`)); }
    catch (cause) { setError((cause as Error).message); }
  }
  return <><h1 className="text-4xl font-bold">Moderation</h1><Status message={message} error={error} />
    <section className="card grid gap-4 md:grid-cols-2"><label>Warnings before kick<input type="number" min="1" value={value.warn_kick_threshold} onChange={e => setValue({ ...value, warn_kick_threshold: Number(e.target.value) })} /></label><label>Warnings before ban<input type="number" min="1" value={value.warn_ban_threshold} onChange={e => setValue({ ...value, warn_ban_threshold: Number(e.target.value) })} /></label><ChannelSelect label="Moderation log channel" channels={guild.channels} value={value.log_channel_id} onChange={log_channel_id => setValue({ ...value, log_channel_id })} /><label className="flex items-center gap-2"><input type="checkbox" checked={value.dm_on_warn} onChange={e => setValue({ ...value, dm_on_warn: e.target.checked })} />DM members on warning</label></section>
    <section className="card space-y-3"><h2 className="text-xl font-semibold">Warnings</h2><div className="flex gap-2"><input placeholder="Filter by Discord user ID" value={userId} onChange={e => setUserId(e.target.value)} /><button className="secondary" onClick={search}>Search</button></div>{warnings.length ? <ul className="space-y-2 text-sm">{warnings.map(row => <li key={row.id}>#{row.id} &lt;@{row.user_id}&gt; — {row.reason} (by {row.moderator_id}, {new Date(row.created_at).toLocaleString()})</li>)}</ul> : <p>No warnings found.</p>}</section>
    <div className="save-bar"><button className="primary" onClick={save}>Save settings</button></div>
  </>;
}
