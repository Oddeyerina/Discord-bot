'use client';

import { useState } from 'react';
import ChannelSelect from '@/components/ChannelSelect';
import RoleSelect from '@/components/RoleSelect';
import EmbedEditor from '@/components/EmbedEditor';
import Status from '@/components/Status';
import { api, emptyEmbed, type Embed } from '@/lib/api';
import { useConfig } from '@/hooks/useConfig';

type Counter = { label: string; role_id: string };
type Config = { channel_id: string; update_interval_seconds: number; enabled: boolean; role_counters: Counter[]; embed: Embed };
const defaults: Config = { channel_id: '', update_interval_seconds: 300, enabled: false,
  role_counters: [], embed: { ...emptyEmbed, title: 'Server Stats', description: 'Members: {total_members}\nOnline: {online}' } };

export default function StatsPage() {
  const { value, setValue, guild, message, error, busy, save } = useConfig('/stats/config', defaults);
  const [postMessage, setPostMessage] = useState('');
  const [postError, setPostError] = useState('');
  const updateCounter = (index: number, patch: Partial<Counter>) => setValue({ ...value,
    role_counters: value.role_counters.map((item, position) => position === index ? { ...item, ...patch } : item) });
  async function postNow() {
    setPostError(''); setPostMessage('');
    try {
      await api('/stats/config', { method: 'PUT', body: JSON.stringify(value) });
      const result = await api<{ task_id: number }>('/stats/resend', { method: 'POST' });
      setPostMessage(`Stats task #${result.task_id} queued.`);
    } catch (cause) { setPostError((cause as Error).message); }
  }
  return <><header><h1 className="text-3xl font-bold">Live Server Stats</h1>
    <p className="text-slate-400">The bot edits one stats message at the configured interval.</p></header>
    <Status message={message || postMessage} error={error || postError} />
    <div className="flex gap-3"><button className="secondary" disabled={busy} onClick={save}>Save</button>
      <button className="primary" disabled={busy || !value.channel_id} onClick={postNow}>Post / Update now</button></div>
    <section className="card grid gap-4 md:grid-cols-2">
      <ChannelSelect label="Stats channel" value={value.channel_id} channels={guild.channels}
        onChange={channel_id => setValue({ ...value, channel_id })} />
      <label>Update interval (seconds)<input type="number" min={60} max={86400}
        value={value.update_interval_seconds} onChange={event => setValue({ ...value, update_interval_seconds: Number(event.target.value) })} /></label>
      <label className="flex items-center gap-2"><input type="checkbox" checked={value.enabled}
        onChange={event => setValue({ ...value, enabled: event.target.checked })} />Enabled</label>
    </section>
    <section className="space-y-4"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Role counters</h2>
      <button className="secondary" onClick={() => setValue({ ...value, role_counters: [...value.role_counters, { label: '', role_id: '' }] })}>Add counter</button></div>
      {value.role_counters.map((counter, index) => <div className="card grid gap-4 md:grid-cols-[1fr_2fr_auto]" key={index}>
        <label>Label<input value={counter.label} onChange={event => updateCounter(index, { label: event.target.value })} /></label>
        <RoleSelect label="Role" roles={guild.roles} value={counter.role_id} onChange={role_id => updateCounter(index, { role_id })} />
        <button className="secondary" onClick={() => setValue({ ...value, role_counters: value.role_counters.filter((_, position) => position !== index) })}>Remove</button>
      </div>)}</section>
    <p className="text-sm text-slate-400">Stats placeholders: {'{total_members}'}, {'{human_members}'}, {'{bot_members}'}, {'{online}'}, {'{in_voice}'}, {'{artist_count}'}, {'{verified_count}'}, {'{booster_count}'}, {'{boost_count}'}, {'{boost_level}'}, {'{boosts_needed}'}, {'{timestamp}'}. Role counters use {'{role_count_label}'} with a lowercase label slug. Online requires Presence Intent.</p>
    <EmbedEditor title="Stats embed" value={value.embed || emptyEmbed} onChange={embed => setValue({ ...value, embed })} />
  </>;
}
