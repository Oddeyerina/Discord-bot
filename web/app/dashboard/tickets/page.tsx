'use client';

import EmbedEditor from '@/components/EmbedEditor';
import ChannelSelect from '@/components/ChannelSelect';
import MultiSelect from '@/components/MultiSelect';
import EmojiSelect from '@/components/EmojiSelect';
import Status from '@/components/Status';
import { useEffect, useRef, useState } from 'react';
import { api, emptyEmbed, type Embed, type GuildData } from '@/lib/api';

type Reason = { id?: number; draftKey?: number; label: string; emoji: string; description: string; support_role_ids: string[]; questions: string[] };
type Priority = { id?: number; label: string; emoji: string; color: string };
type Autoresponse = { trigger_keyword: string; response_text: string; enabled: boolean };
type Quickreply = { label: string; response_text: string };
type Config = { id?: number; name: string; channel_id: string; embed: Embed; extra_config: { thread_name_pattern: string; transcript_channel_id: string; claim_label: string; close_label: string; claim_style: string; close_style: string; inactivity_hours?: number; inactivity_warning_hours?: number }; reasons: Reason[]; priorities: Priority[]; autoresponses: Autoresponse[]; quickreplies: Quickreply[] };
type Ticket = { id: number; thread_id: string; user_id: string; status: string; assigned_to: string | null; created_at: string };
const defaults: Config = { name: '', channel_id: '', embed: { ...emptyEmbed, title: 'Open a ticket' }, extra_config: { thread_name_pattern: 'ticket-{username}', transcript_channel_id: '', claim_label: 'Claim', close_label: 'Close', claim_style: 'primary', close_style: 'danger', inactivity_hours: 72, inactivity_warning_hours: 24 }, reasons: [], priorities: [], autoresponses: [], quickreplies: [] };

export default function TicketsPage() {
  const nextDraftKey = useRef(0);
  const [panels, setPanels] = useState<Config[]>([]);
  const [value, setValue] = useState<Config>(defaults);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [guild, setGuild] = useState<GuildData>({ channels: [], roles: [], emojis: [] });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const editing = Boolean(expanded[String(value.id ?? 'new')]);
  function toggle(panel: Config | null) {
    const key = String(panel?.id ?? 'new');
    setValue(panel || { ...defaults, embed: { ...defaults.embed }, extra_config: { ...defaults.extra_config }, reasons: [], priorities: [], autoresponses: [], quickreplies: [] });
    setExpanded(previous => {
      const next: Record<string, boolean> = {};
      for (const current of Object.keys(previous)) next[current] = false;
      next[key] = !previous[key];
      return next;
    });
  }
  useEffect(() => {
    Promise.all([api<Config[]>('/tickets/config'), api<GuildData>('/guild/data'), api<Ticket[]>('/tickets')])
      .then(([items, data, rows]) => { setPanels(items); setGuild(data); setTickets(rows); }).catch(cause => setError((cause as Error).message));
  }, []);
  async function persist(): Promise<Config> {
    const saved = await api<Config>(value.id ? `/tickets/config/${value.id}` : '/tickets/config',
      { method: value.id ? 'PUT' : 'POST', body: JSON.stringify(value) });
    setValue(saved);
    if (!value.id) setExpanded({ [String(saved.id)]: true });
    setPanels(current => [...current.filter(item => item.id !== saved.id), saved].sort((a, b) => (a.id || 0) - (b.id || 0)));
    return saved;
  }
  async function save() {
    setBusy(true); setError(''); setMessage('');
    try { await persist(); setMessage('Saved.'); }
    catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }
  async function publish(panelId?: number) {
    setBusy(true); setError(''); setMessage('');
    try {
      const id = panelId || (await persist()).id;
      const result = await api<{ task_id: number }>(`/panels/tickets/${id}/publish`, { method: 'POST' });
      setMessage(`Panel task #${result.task_id} queued.`);
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }
  async function remove(panelId: number) {
    if (!window.confirm('Delete this ticket panel?')) return;
    setBusy(true); setError(''); setMessage('');
    try { await api(`/tickets/config/${panelId}`, { method: 'DELETE' });
      setPanels(current => current.filter(item => item.id !== panelId));
      setExpanded(previous => ({ ...previous, [String(panelId)]: false }));
      setMessage('Panel deletion queued.'); }
    catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }
  const updateReason = (index: number, patch: Partial<Reason>) => setValue({ ...value, reasons: value.reasons.map((r, i) => i === index ? { ...r, ...patch } : r) });
  return <><header><h1 className="text-4xl font-bold">Tickets</h1><p className="text-slate-400">Choose a panel channel and the reasons users can select. Each reason&apos;s support roles grant private thread access; they are pinged only after the user clicks Done.</p></header><Status message={message} error={error} />
    <button type="button" className="primary" onClick={() => toggle(null)}>New ticket panel</button>
    <section className="grid gap-4 md:grid-cols-2">{panels.map(panel => <div className="card space-y-3" key={panel.id}>
      <h2 className="text-xl font-semibold"><button type="button" aria-expanded={Boolean(expanded[String(panel.id)])} onClick={() => toggle(panel)} className="text-left">{panel.name || `Ticket panel #${panel.id}`}</button></h2>
      <p className="text-sm text-slate-400">{guild.channels.find(channel => channel.id === panel.channel_id)?.name || panel.channel_id}</p>
      <div className="flex flex-wrap gap-2"><button type="button" className="secondary" onClick={() => toggle(panel)}>{expanded[String(panel.id)] ? 'Collapse' : 'Edit'}</button>
        <button className="primary" disabled={busy} onClick={() => publish(panel.id)}>Post / Update Panel</button>
        <button className="secondary" disabled={busy} onClick={() => panel.id && remove(panel.id)}>Delete</button></div>
    </div>)}</section>
    <section className="card space-y-2"><h2 className="text-xl font-semibold">Recent tickets</h2>{tickets.length ? <ul>{tickets.map(ticket => <li key={ticket.id}>#{ticket.id} — User {ticket.user_id} — {ticket.status} — Assigned: {ticket.assigned_to || 'Unassigned'} — Thread {ticket.thread_id}</li>)}</ul> : <p>No tickets yet.</p>}</section>
    {editing && <><h2 className="text-xl font-semibold">{value.id ? 'Edit ticket panel' : 'New ticket panel'}</h2>
    <label>Panel name<input maxLength={100} value={value.name || ''} onChange={event => setValue({ ...value, name: event.target.value })} /></label>
    <section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Panel channel" value={value.channel_id} channels={guild.channels} onChange={channel_id => setValue({ ...value, channel_id })} /><ChannelSelect label="Transcript channel" value={value.extra_config?.transcript_channel_id} channels={guild.channels} onChange={transcript_channel_id => setValue({ ...value, extra_config: { ...value.extra_config, transcript_channel_id } })} /><label>Thread name pattern<input value={value.extra_config?.thread_name_pattern || ''} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, thread_name_pattern: e.target.value } })} /></label><label>Claim button label<input value={value.extra_config?.claim_label || ''} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, claim_label: e.target.value } })} /></label><label>Close button label<input value={value.extra_config?.close_label || ''} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, close_label: e.target.value } })} /></label>{(['claim_style', 'close_style'] as const).map(field => <label key={field}>{field === 'claim_style' ? 'Claim' : 'Close'} button color<select value={value.extra_config?.[field] || 'primary'} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, [field]: e.target.value } })}><option value="primary">Blue</option><option value="secondary">Gray</option><option value="success">Green</option><option value="danger">Red</option></select></label>)}</section>
    <section className="card grid gap-4 md:grid-cols-2"><label>Close after inactivity (hours)<input type="number" min="0" value={value.extra_config?.inactivity_hours ?? 72} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, inactivity_hours: Number(e.target.value) } })} /></label><label>Warn after inactivity (hours)<input type="number" min="0" value={value.extra_config?.inactivity_warning_hours ?? 24} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, inactivity_warning_hours: Number(e.target.value) } })} /></label></section>
    <EmbedEditor title="Ticket panel embed" value={value.embed || emptyEmbed} onChange={embed => setValue({ ...value, embed })} />
    <section className="space-y-5"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Reasons</h2><button className="secondary" onClick={() => setValue({ ...value, reasons: [...value.reasons, { draftKey: ++nextDraftKey.current, label: '', emoji: '', description: '', support_role_ids: [], questions: [] }] })}>Add reason</button></div>{value.reasons.map((reason, index) => <div className="card space-y-5" key={reason.id ?? `new-${reason.draftKey}`}><div className="grid gap-4 md:grid-cols-3"><label>Label<input value={reason.label} onChange={e => updateReason(index, { label: e.target.value })} /></label><EmojiSelect value={reason.emoji || ''} onChange={emoji => updateReason(index, { emoji })} emojis={guild.emojis} /><label>Description<input value={reason.description} onChange={e => updateReason(index, { description: e.target.value })} /></label></div><MultiSelect label="Support roles" options={guild.roles} value={reason.support_role_ids} onChange={support_role_ids => updateReason(index, { support_role_ids })} /><label>Follow-up questions (one per line)<textarea rows={3} value={reason.questions.join('\n')} onChange={e => updateReason(index, { questions: e.target.value.split('\n').filter(Boolean) })} /></label><button className="secondary" onClick={() => setValue({ ...value, reasons: value.reasons.filter((_, i) => i !== index) })}>Remove reason</button></div>)}</section>
    <section className="space-y-5"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Priorities</h2><button className="secondary" onClick={() => setValue({ ...value, priorities: [...value.priorities, { label: '', emoji: '', color: '#5865F2' }] })}>Add priority</button></div><p className="text-sm text-slate-400">Priorities appear in this order. Leave the list empty to skip priority selection.</p>{value.priorities.map((priority, index) => <div className="card grid gap-4 md:grid-cols-4" key={priority.id ?? `priority-${index}`}><label>Label<input value={priority.label} onChange={event => setValue({ ...value, priorities: value.priorities.map((row, i) => i === index ? { ...row, label: event.target.value } : row) })} /></label><EmojiSelect value={priority.emoji || ''} onChange={emoji => setValue({ ...value, priorities: value.priorities.map((row, i) => i === index ? { ...row, emoji } : row) })} emojis={guild.emojis} /><label>Color<input type="color" value={priority.color} onChange={event => setValue({ ...value, priorities: value.priorities.map((row, i) => i === index ? { ...row, color: event.target.value } : row) })} /></label><div className="flex gap-2"><button className="secondary" disabled={index === 0} onClick={() => { const rows = [...value.priorities]; [rows[index - 1], rows[index]] = [rows[index], rows[index - 1]]; setValue({ ...value, priorities: rows }); }}>Up</button><button className="secondary" disabled={index === value.priorities.length - 1} onClick={() => { const rows = [...value.priorities]; [rows[index + 1], rows[index]] = [rows[index], rows[index + 1]]; setValue({ ...value, priorities: rows }); }}>Down</button><button className="secondary" onClick={() => setValue({ ...value, priorities: value.priorities.filter((_, i) => i !== index) })}>Remove</button></div></div>)}</section>
    <section className="space-y-5"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Auto responses</h2><button className="secondary" onClick={() => setValue({ ...value, autoresponses: [...value.autoresponses, { trigger_keyword: '', response_text: '', enabled: true }] })}>Add response</button></div>{value.autoresponses.map((row, index) => <div className="card grid gap-4 md:grid-cols-2" key={index}><label>Trigger keyword<input value={row.trigger_keyword} onChange={event => setValue({ ...value, autoresponses: value.autoresponses.map((item, i) => i === index ? { ...item, trigger_keyword: event.target.value } : item) })} /></label><label>Response text<textarea maxLength={2000} value={row.response_text} onChange={event => setValue({ ...value, autoresponses: value.autoresponses.map((item, i) => i === index ? { ...item, response_text: event.target.value } : item) })} /></label><label className="flex items-center gap-2"><input type="checkbox" checked={row.enabled} onChange={event => setValue({ ...value, autoresponses: value.autoresponses.map((item, i) => i === index ? { ...item, enabled: event.target.checked } : item) })} />Enabled</label><button className="secondary" onClick={() => setValue({ ...value, autoresponses: value.autoresponses.filter((_, i) => i !== index) })}>Remove</button></div>)}</section>
    <section className="space-y-5"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Quick Replies</h2><button className="secondary" onClick={() => setValue({ ...value, quickreplies: [...value.quickreplies, { label: '', response_text: '' }] })}>Add reply</button></div>{value.quickreplies.map((row, index) => <div className="card grid gap-4 md:grid-cols-2" key={index}><label>Label<input value={row.label} onChange={event => setValue({ ...value, quickreplies: value.quickreplies.map((item, i) => i === index ? { ...item, label: event.target.value } : item) })} /></label><label>Response text<textarea maxLength={2000} value={row.response_text} onChange={event => setValue({ ...value, quickreplies: value.quickreplies.map((item, i) => i === index ? { ...item, response_text: event.target.value } : item) })} /></label><button className="secondary" onClick={() => setValue({ ...value, quickreplies: value.quickreplies.filter((_, i) => i !== index) })}>Remove</button></div>)}</section>
    <div className="save-bar"><button type="button" disabled={busy} className="secondary" onClick={save}>Save</button><button type="button" disabled={busy || !value.channel_id} className="primary" onClick={() => publish()}>Post / Update Panel</button></div>
    </>}
  </>;
}
