'use client';

import EmbedEditor from '@/components/EmbedEditor';
import ChannelSelect from '@/components/ChannelSelect';
import MultiSelect from '@/components/MultiSelect';
import EmojiSelect from '@/components/EmojiSelect';
import Status from '@/components/Status';
import { useRef } from 'react';
import { emptyEmbed, type Embed } from '@/lib/api';
import { useConfig } from '@/hooks/useConfig';

type Reason = { id?: number; draftKey?: number; label: string; emoji: string; description: string; support_role_ids: string[]; questions: string[] };
type Config = { channel_id: string; embed: Embed; extra_config: { thread_name_pattern: string; transcript_channel_id: string; claim_label: string; close_label: string; claim_style: string; close_style: string }; reasons: Reason[] };
const defaults: Config = { channel_id: '', embed: { ...emptyEmbed, title: 'Open a ticket' }, extra_config: { thread_name_pattern: 'ticket-{username}', transcript_channel_id: '', claim_label: 'Claim', close_label: 'Close', claim_style: 'primary', close_style: 'danger' }, reasons: [] };

export default function TicketsPage() {
  const nextDraftKey = useRef(0);
  const { value, setValue, guild, message, error, busy, save, publish } = useConfig('/tickets/config', defaults);
  const updateReason = (index: number, patch: Partial<Reason>) => setValue({ ...value, reasons: value.reasons.map((r, i) => i === index ? { ...r, ...patch } : r) });
  return <><header><h1 className="text-3xl font-bold">Tickets</h1><p className="text-slate-400">Choose a panel channel and the reasons users can select. Each reason&apos;s support roles grant private thread access; they are pinged only after the user clicks Done.</p></header><Status message={message} error={error} />
    <section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Panel channel" value={value.channel_id} channels={guild.channels} onChange={channel_id => setValue({ ...value, channel_id })} /><ChannelSelect label="Transcript channel" value={value.extra_config?.transcript_channel_id} channels={guild.channels} onChange={transcript_channel_id => setValue({ ...value, extra_config: { ...value.extra_config, transcript_channel_id } })} /><label>Thread name pattern<input value={value.extra_config?.thread_name_pattern || ''} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, thread_name_pattern: e.target.value } })} /></label><label>Claim button label<input value={value.extra_config?.claim_label || ''} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, claim_label: e.target.value } })} /></label><label>Close button label<input value={value.extra_config?.close_label || ''} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, close_label: e.target.value } })} /></label>{(['claim_style', 'close_style'] as const).map(field => <label key={field}>{field === 'claim_style' ? 'Claim' : 'Close'} button color<select value={value.extra_config?.[field] || 'primary'} onChange={e => setValue({ ...value, extra_config: { ...value.extra_config, [field]: e.target.value } })}><option value="primary">Blue</option><option value="secondary">Gray</option><option value="success">Green</option><option value="danger">Red</option></select></label>)}</section>
    <EmbedEditor title="Ticket panel embed" value={value.embed || emptyEmbed} onChange={embed => setValue({ ...value, embed })} />
    <section className="space-y-4"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Reasons</h2><button className="secondary" onClick={() => setValue({ ...value, reasons: [...value.reasons, { draftKey: ++nextDraftKey.current, label: '', emoji: '', description: '', support_role_ids: [], questions: [] }] })}>Add reason</button></div>{value.reasons.map((reason, index) => <div className="card space-y-4" key={reason.id ?? `new-${reason.draftKey}`}><div className="grid gap-4 md:grid-cols-3"><label>Label<input value={reason.label} onChange={e => updateReason(index, { label: e.target.value })} /></label><EmojiSelect value={reason.emoji || ''} onChange={emoji => updateReason(index, { emoji })} emojis={guild.emojis} /><label>Description<input value={reason.description} onChange={e => updateReason(index, { description: e.target.value })} /></label></div><MultiSelect label="Support roles" options={guild.roles} value={reason.support_role_ids} onChange={support_role_ids => updateReason(index, { support_role_ids })} /><label>Follow-up questions (one per line)<textarea rows={3} value={reason.questions.join('\n')} onChange={e => updateReason(index, { questions: e.target.value.split('\n').filter(Boolean) })} /></label><button className="secondary" onClick={() => setValue({ ...value, reasons: value.reasons.filter((_, i) => i !== index) })}>Remove reason</button></div>)}</section>
    <div className="flex gap-3"><button disabled={busy} className="secondary" onClick={save}>Save</button><button disabled={busy || !value.channel_id} className="primary" onClick={() => publish('tickets')}>Post / Update Panel</button></div>
  </>;
}
