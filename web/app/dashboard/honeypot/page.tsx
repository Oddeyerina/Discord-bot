'use client';

import ChannelSelect from '@/components/ChannelSelect';
import MultiSelect from '@/components/MultiSelect';
import EmbedEditor from '@/components/EmbedEditor';
import Status from '@/components/Status';
import { emptyEmbed, type Embed } from '@/lib/api';
import { useConfig } from '@/hooks/useConfig';

type Config = { channel_id: string; action: 'kick' | 'ban' | 'timeout'; timeout_seconds: number; log_channel_id: string; delete_message: boolean; dm_user: boolean; whitelist_role_ids: string[]; embed: Embed };
const defaults: Config = { channel_id: '', action: 'kick', timeout_seconds: 3600, log_channel_id: '', delete_message: true, dm_user: false, whitelist_role_ids: [], embed: { ...emptyEmbed, title: 'Protected channel' } };

export default function HoneypotPage() {
  const { value, setValue, guild, message, error, busy, save, publish } = useConfig('/honeypot/config', defaults);
  return <><header><h1 className="text-3xl font-bold">Honeypot</h1><p className="text-slate-400">Messages and reactions in this channel trigger the selected action.</p></header><Status message={message} error={error} />
    <section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Honeypot channel" channels={guild.channels} value={value.channel_id} onChange={channel_id => setValue({ ...value, channel_id })} /><ChannelSelect label="Log channel" channels={guild.channels} value={value.log_channel_id} onChange={log_channel_id => setValue({ ...value, log_channel_id })} /><label>Action<select value={value.action} onChange={e => setValue({ ...value, action: e.target.value as Config['action'] })}><option value="kick">Kick</option><option value="ban">Ban</option><option value="timeout">Timeout</option></select></label>{value.action === 'timeout' && <label>Timeout seconds<input type="number" min="1" value={value.timeout_seconds} onChange={e => setValue({ ...value, timeout_seconds: Number(e.target.value) })} /></label>}<MultiSelect label="Whitelist roles" options={guild.roles} value={value.whitelist_role_ids} onChange={whitelist_role_ids => setValue({ ...value, whitelist_role_ids })} /><label className="flex items-center gap-2"><input className="w-auto" type="checkbox" checked={value.delete_message} onChange={e => setValue({ ...value, delete_message: e.target.checked })} />Delete triggering message</label><label className="flex items-center gap-2"><input className="w-auto" type="checkbox" checked={value.dm_user} onChange={e => setValue({ ...value, dm_user: e.target.checked })} />DM the user</label></section>
    <EmbedEditor title="Decoy panel embed" value={value.embed || emptyEmbed} onChange={embed => setValue({ ...value, embed })} /><div className="flex gap-3"><button className="secondary" disabled={busy} onClick={save}>Save</button><button className="primary" disabled={busy || !value.channel_id} onClick={() => publish('honeypot')}>Post / Update Panel</button></div>
  </>;
}
