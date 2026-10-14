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
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [taskMessage, setTaskMessage] = useState('');
  const [taskError, setTaskError] = useState('');
  const [posting, setPosting] = useState(false);
  const update = (index: number, patch: Partial<Sticky>) => setValue({ channels: value.channels.map((row, i) => i === index ? { ...row, ...patch } : row) });

  function toggle(index: number) {
    const key = String(index);
    setExpanded(previous => {
      const next: Record<string, boolean> = {};
      for (const current of Object.keys(previous)) next[current] = false;
      next[key] = !previous[key];
      return next;
    });
  }

  async function waitForTask(taskId: number) {
    for (let attempt = 0; attempt < 8; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      const tasks = await api<{ id: number; status: string; error: string | null }[]>('/tasks');
      const task = tasks.find(item => item.id === taskId);
      if (task?.status === 'done') { setTaskMessage(`Sticky task #${taskId} completed.`); return; }
      if (task?.status === 'failed') throw new Error(task.error || 'Sticky task failed.');
    }
  }

  async function post(channelId: string) {
    setTaskError(''); setTaskMessage(''); setPosting(true);
    try {
      await api('/sticky/config', { method: 'PUT', body: JSON.stringify(value) });
      const result = await api<{ task_id: number }>(`/sticky/post/${channelId}`, { method: 'POST' });
      setTaskMessage(`Sticky task #${result.task_id} queued.`);
      await waitForTask(result.task_id);
    } catch (cause) { setTaskError((cause as Error).message); }
    finally { setPosting(false); }
  }

  async function resendAll() {
    setTaskError(''); setTaskMessage(''); setPosting(true);
    try {
      await api('/sticky/config', { method: 'PUT', body: JSON.stringify(value) });
      const result = await api<{ task_id: number }>('/sticky/resend-all', { method: 'POST' });
      setTaskMessage(`Resend task #${result.task_id} queued.`);
      await waitForTask(result.task_id);
    } catch (cause) { setTaskError((cause as Error).message); }
    finally { setPosting(false); }
  }

  async function remove(index: number) {
    if (!window.confirm('Delete this sticky configuration?')) return;
    setTaskError(''); setTaskMessage('');
    try {
      const next = { channels: value.channels.filter((_, i) => i !== index) };
      const saved = await api<Config>('/sticky/config', { method: 'PUT', body: JSON.stringify(next) });
      setValue(saved); setExpanded({}); setTaskMessage('Sticky configuration deleted.');
    } catch (cause) { setTaskError((cause as Error).message); }
  }

  return <><header><h1 className="text-4xl font-bold">Sticky Messages</h1><p className="text-slate-400">Keep an embed visible in each selected channel. A refresh can ping one role after the cooldown.</p></header>
    <Status message={message || taskMessage} error={error || taskError} />
    <button type="button" className="secondary" onClick={() => {
      setExpanded({ [String(value.channels.length)]: true });
      setValue({ channels: [...value.channels, { channel_id: '', role_id: null, sticky_embed: { ...emptyEmbed }, cooldown_seconds: 60, enabled: true }] });
    }}>Add channel</button>
    <section className="space-y-5">{value.channels.map((row, index) => {
      const channelName = guild.channels.find(channel => channel.id === row.channel_id)?.name || row.channel_id || 'New sticky';
      const roleName = guild.roles.find(role => role.id === row.role_id)?.name || (row.role_id ? row.role_id : 'None');
      const open = Boolean(expanded[String(index)]);
      return <div className="card space-y-5" key={`${row.channel_id || 'new'}-${index}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <button type="button" aria-expanded={open} onClick={() => toggle(index)} className="min-w-0 flex-1 text-left">
            <h2 className="text-xl font-semibold">{channelName}</h2>
            <p className="text-sm text-slate-400">Ping role: {roleName} · Cooldown: {row.cooldown_seconds}s · {row.enabled ? 'Enabled' : 'Disabled'}</p>
          </button>
          <div className="flex flex-wrap gap-2"><button type="button" className="secondary" onClick={() => toggle(index)}>{open ? 'Collapse' : 'Edit'}</button>
            <button type="button" className="primary" disabled={!row.channel_id || busy || posting} onClick={() => post(row.channel_id)}>Resend</button>
            <button type="button" className="secondary" disabled={busy || posting} onClick={() => remove(index)}>Delete</button></div>
        </div>
        {open && <div className="space-y-5 border-t border-slate-800 pt-5">
          <div className="grid gap-5 md:grid-cols-2"><ChannelSelect label="Sticky channel" value={row.channel_id} channels={guild.channels} onChange={channel_id => update(index, { channel_id })} /><RoleSelect label="Role to ping (optional)" value={row.role_id} roles={guild.roles} onChange={role_id => update(index, { role_id: role_id || null })} /><label>Cooldown (seconds)<input type="number" min={0} max={86400} value={row.cooldown_seconds} onChange={event => update(index, { cooldown_seconds: Number(event.target.value) })} /></label><label className="flex items-center gap-2"><input type="checkbox" checked={row.enabled} onChange={event => update(index, { enabled: event.target.checked })} />Enabled</label></div>
          <EmbedEditor title="Sticky embed" value={row.sticky_embed} onChange={sticky_embed => update(index, { sticky_embed })} />
          {row.role_id && ![row.sticky_embed.title, row.sticky_embed.description, row.sticky_embed.footer].some(text => text?.includes('{role}')) && <p className="text-sm text-amber-300">Tip: add {'{role}'} to the embed text to show a clickable mention inside the embed. The role will still be pinged as a separate message.</p>}
        </div>}
      </div>;
    })}</section>
    <div className="save-bar"><button type="button" className="primary" disabled={busy} onClick={save}>Save</button><button type="button" className="secondary" disabled={busy || posting || !value.channels.some(row => row.enabled && row.channel_id)} onClick={resendAll}>Resend all stickies</button></div>
  </>;
}
