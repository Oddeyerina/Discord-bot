'use client';

import { useEffect, useState } from 'react';
import ChannelSelect from '@/components/ChannelSelect';
import EmbedEditor from '@/components/EmbedEditor';
import Status from '@/components/Status';
import { api, emptyEmbed, type Embed } from '@/lib/api';
import { useConfig } from '@/hooks/useConfig';

type Config = { channel_id: string; timezone: string; enabled: boolean; announcement_embed: Embed; label_embeds: Record<string, Embed> };
type DateRow = { user_id: string; date_day: number; date_month: number; date_year: number | null; label: string };
const defaults: Config = { channel_id: '', timezone: 'Europe/Berlin', enabled: false, announcement_embed: { ...emptyEmbed, title: 'Happy {label}!', description: 'Congratulations {user}! {age}' }, label_embeds: {} };

export default function RememberingPage() {
  const { value, setValue, guild, message, error, busy, save } = useConfig('/remembering/config', defaults);
  const [dates, setDates] = useState<DateRow[]>([]);
  const [newLabel, setNewLabel] = useState('');
  useEffect(() => { api<DateRow[]>('/remembering/dates').then(setDates).catch(() => undefined); }, []);
  return <><header><h1 className="text-3xl font-bold">Remembering Dates</h1><p className="text-slate-400">Members save dates with /birthday. Announcements run daily at 08:00 UTC.</p></header><Status message={message} error={error} />
    <section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Announcement channel" value={value.channel_id} channels={guild.channels} onChange={channel_id => setValue({ ...value, channel_id })} /><label>Timezone<input value={value.timezone} onChange={event => setValue({ ...value, timezone: event.target.value })} /></label><label className="flex items-center gap-2"><input type="checkbox" checked={value.enabled} onChange={event => setValue({ ...value, enabled: event.target.checked })} />Enabled</label></section>
    <EmbedEditor title="Announcement embed" value={value.announcement_embed} onChange={announcement_embed => setValue({ ...value, announcement_embed })} />
    <section className="space-y-4"><h2 className="text-xl font-semibold">Embeds by date label</h2><p className="text-sm text-slate-400">A matching label uses its own embed. Other labels use the announcement embed.</p>
      <div className="flex gap-3"><input placeholder="Label, e.g. Anniversary" value={newLabel} onChange={event => setNewLabel(event.target.value)} /><button className="secondary" disabled={!newLabel.trim()} onClick={() => { const label = newLabel.trim(); setValue({ ...value, label_embeds: { ...(value.label_embeds || {}), [label]: { ...emptyEmbed } } }); setNewLabel(''); }}>Add label</button></div>
      {Object.entries(value.label_embeds || {}).map(([label, embed]) => <div className="card space-y-3" key={label}><div className="flex items-center justify-between"><h3 className="font-semibold">{label}</h3><button className="secondary" onClick={() => { const next = { ...value.label_embeds }; delete next[label]; setValue({ ...value, label_embeds: next }); }}>Remove</button></div><EmbedEditor title={`${label} embed`} value={embed} onChange={updated => setValue({ ...value, label_embeds: { ...value.label_embeds, [label]: updated } })} /></div>)}
    </section>
    <button className="primary" disabled={busy} onClick={save}>Save</button>
    <section className="card"><h2 className="text-xl font-semibold">Saved dates</h2><div className="space-y-2 mt-3">{dates.length ? dates.map((row, index) => <p key={index}>{row.user_id} — {row.date_day.toString().padStart(2, '0')}/{row.date_month.toString().padStart(2, '0')}{row.date_year ? `/${row.date_year}` : ''} — {row.label}</p>) : <p className="text-slate-400">No dates saved yet.</p>}</div></section>
  </>;
}
