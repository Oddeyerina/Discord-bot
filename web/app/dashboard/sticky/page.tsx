'use client';

import { useState } from 'react';
import ChannelSelect from '@/components/ChannelSelect';
import RoleSelect from '@/components/RoleSelect';
import EmbedEditor from '@/components/EmbedEditor';
import Status from '@/components/Status';
import { api, emptyEmbed, type Embed } from '@/lib/api';
import { useConfig } from '@/hooks/useConfig';

type Sticky = { channel_id: string; role_id: string | null; sticky_embed: Embed; cooldown_seconds: number; enabled: boolean };
type Config = { channels: Sticky[] };
const defaults: Config = { channels: [] };

export default function StickyPage() {
  const { value, setValue, guild, message, error, busy, save } = useConfig('/sticky/config', defaults);
  const [taskMessage, setTaskMessage] = useState('');
  const [taskError, setTaskError] = useState('');
  const update = (index: number, patch: Partial<Sticky>) => setValue({ channels: value.channels.map((row, i) => i === index ? { ...row, ...patch } : row) });
  async function post(channelId: string) {
    setTaskError(''); setTaskMessage('');
    try {
      await api('/sticky/config', { method: 'PUT', body: JSON.stringify(value) });
      const result = await api<{ task_id: number }>(`/sticky/post/${channelId}`, { method: 'POST' });
      setTaskMessage(`Sticky task #${result.task_id} queued.`);
    } catch (cause) { setTaskError((cause as Error).message); }
  }
  return <><header><h1 className="text-3xl font-bold">Sticky Messages</h1><p className="text-slate-400">Keep an embed visible in each selected channel. A refresh can ping one role after the cooldown.</p></header>
    <Status message={message || taskMessage} error={error || taskError} />
    {value.channels.map((row, index) => <section className="card space-y-4" key={index}>
      <div className="grid gap-4 md:grid-cols-2"><ChannelSelect label="Sticky channel" value={row.channel_id} channels={guild.channels} onChange={channel_id => update(index, { channel_id })} /><RoleSelect label="Role to ping (optional)" value={row.role_id} roles={guild.roles} onChange={role_id => update(index, { role_id: role_id || null })} /><label>Cooldown (seconds)<input type="number" min={0} max={86400} value={row.cooldown_seconds} onChange={event => update(index, { cooldown_seconds: Number(event.target.value) })} /></label><label className="flex items-center gap-2"><input type="checkbox" checked={row.enabled} onChange={event => update(index, { enabled: event.target.checked })} />Enabled</label></div>
      <EmbedEditor title="Sticky embed" value={row.sticky_embed} onChange={sticky_embed => update(index, { sticky_embed })} />
      <div className="flex gap-3"><button className="secondary" onClick={() => setValue({ channels: value.channels.filter((_, i) => i !== index) })}>Remove</button><button className="primary" disabled={!row.channel_id || busy} onClick={() => post(row.channel_id)}>Sticky now</button></div>
    </section>)}
    <div className="flex gap-3"><button className="secondary" onClick={() => setValue({ channels: [...value.channels, { channel_id: '', role_id: null, sticky_embed: { ...emptyEmbed }, cooldown_seconds: 60, enabled: true }] })}>Add channel</button><button className="primary" disabled={busy} onClick={save}>Save</button></div>
  </>;
}
