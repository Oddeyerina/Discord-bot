'use client';

import { useEffect, useState } from 'react';
import ChannelSelect from '@/components/ChannelSelect';
import RoleSelect from '@/components/RoleSelect';
import EmbedEditor from '@/components/EmbedEditor';
import EmojiSelect from '@/components/EmojiSelect';
import Status from '@/components/Status';
import { api, emptyEmbed, type Embed, type GuildData } from '@/lib/api';

type Mapping = { emoji: string; role_id: string };
type Config = { id?: number; name: string; channel_id: string; embed: Embed; style: 'reaction' | 'select'; extra_config: object; mappings: Mapping[] };
const defaults: Config = { name: '', channel_id: '', embed: { ...emptyEmbed, title: 'Choose your roles' }, style: 'reaction', extra_config: {}, mappings: [] };

export default function ReactionRolesPage() {
  const [panels, setPanels] = useState<Config[]>([]);
  const [value, setValue] = useState<Config>(defaults);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [guild, setGuild] = useState<GuildData>({ channels: [], roles: [], emojis: [] });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const editing = Boolean(expanded[String(value.id ?? 'new')]);
  function toggle(panel: Config | null) {
    const key = String(panel?.id ?? 'new');
    setValue(panel || { ...defaults, embed: { ...defaults.embed }, mappings: [] });
    setExpanded(previous => {
      const next: Record<string, boolean> = {};
      for (const current of Object.keys(previous)) next[current] = false;
      next[key] = !previous[key];
      return next;
    });
  }
  useEffect(() => {
    Promise.all([api<Config[]>('/reaction-roles/config'), api<GuildData>('/guild/data')])
      .then(([items, data]) => { setPanels(items); setGuild(data); })
      .catch(cause => setError((cause as Error).message));
  }, []);
  async function persist(): Promise<Config> {
    const saved = await api<Config>(value.id ? `/reaction-roles/config/${value.id}` : '/reaction-roles/config',
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
      const result = await api<{ task_id: number }>(`/panels/reactionroles/${id}/publish`, { method: 'POST' });
      setMessage(`Panel task #${result.task_id} queued.`);
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }
  async function remove(panelId: number) {
    if (!window.confirm('Delete this reaction-role panel?')) return;
    setBusy(true); setError(''); setMessage('');
    try {
      await api(`/reaction-roles/config/${panelId}`, { method: 'DELETE' });
      setPanels(current => current.filter(item => item.id !== panelId));
      setExpanded(previous => ({ ...previous, [String(panelId)]: false })); setMessage('Panel deletion queued.');
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }
  const change = (index: number, patch: Partial<Mapping>) => setValue({ ...value, mappings: value.mappings.map((m, i) => i === index ? { ...m, ...patch } : m) });
  return <><header><h1 className="text-4xl font-bold">Reaction roles</h1></header><Status message={message} error={error} />
    <button type="button" className="primary" onClick={() => toggle(null)}>New reaction-role panel</button>
    <section className="grid gap-4 md:grid-cols-2">{panels.map(panel => <div className="card space-y-3" key={panel.id}>
      <h2 className="text-xl font-semibold"><button type="button" aria-expanded={Boolean(expanded[String(panel.id)])} onClick={() => toggle(panel)} className="text-left">{panel.name || `Reaction-role panel #${panel.id}`}</button></h2>
      <p className="text-sm text-slate-400">{guild.channels.find(channel => channel.id === panel.channel_id)?.name || panel.channel_id}</p>
      <div className="flex flex-wrap gap-2"><button type="button" className="secondary" onClick={() => toggle(panel)}>{expanded[String(panel.id)] ? 'Collapse' : 'Edit'}</button>
        <button className="primary" disabled={busy} onClick={() => publish(panel.id)}>Post / Update Panel</button>
        <button className="secondary" disabled={busy} onClick={() => panel.id && remove(panel.id)}>Delete</button></div>
    </div>)}</section>
    {editing && <><h2 className="text-xl font-semibold">{value.id ? 'Edit reaction-role panel' : 'New reaction-role panel'}</h2>
      <label>Panel name<input maxLength={100} value={value.name || ''} onChange={event => setValue({ ...value, name: event.target.value })} /></label>
      <section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Panel channel" channels={guild.channels} value={value.channel_id} onChange={channel_id => setValue({ ...value, channel_id })} /><label>Style<select value={value.style} onChange={e => setValue({ ...value, style: e.target.value as Config['style'] })}><option value="reaction">Reactions</option><option value="select">Select menu</option></select></label></section>
      <EmbedEditor value={value.embed || emptyEmbed} onChange={embed => setValue({ ...value, embed })} />
      <section className="space-y-5"><div className="flex justify-between"><h2 className="text-xl font-semibold">Mappings</h2><button className="secondary" onClick={() => setValue({ ...value, mappings: [...value.mappings, { emoji: '', role_id: '' }] })}>Add mapping</button></div>{value.mappings.map((mapping, index) => <div className="card grid items-end gap-4 md:grid-cols-[1fr_2fr_auto]" key={index}><EmojiSelect value={mapping.emoji} onChange={emoji => change(index, { emoji })} emojis={guild.emojis} /><RoleSelect label="Role" roles={guild.roles} value={mapping.role_id} onChange={role_id => change(index, { role_id })} /><button className="secondary" onClick={() => setValue({ ...value, mappings: value.mappings.filter((_, i) => i !== index) })}>Remove</button></div>)}</section>
      <div className="save-bar"><button type="button" className="secondary" disabled={busy} onClick={save}>Save</button><button type="button" className="primary" disabled={busy || !value.channel_id} onClick={() => publish()}>Post / Update Panel</button></div>
    </>}</>;
}
