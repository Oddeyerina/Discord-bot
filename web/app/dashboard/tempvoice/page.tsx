'use client';

import ChannelSelect from '@/components/ChannelSelect';
import Status from '@/components/Status';
import { useConfig } from '@/hooks/useConfig';

type Config = { hub_channel_id: string; category_id: string; control_channel_id: string; name_template: string; user_limit: number; enabled: boolean };
const defaults: Config = { hub_channel_id: '', category_id: '', control_channel_id: '', name_template: "🔊 {user}'s channel", user_limit: 0, enabled: false };

export default function TempVoicePage() {
  const { value, setValue, guild, message, error, busy, save } = useConfig('/tempvoice/config', defaults);
  const sameChannel = Boolean(value.hub_channel_id && value.control_channel_id &&
    value.hub_channel_id === value.control_channel_id);
  return <><header><h1 className="text-4xl font-bold">Temp Voice</h1><p className="text-slate-400">Joining the hub creates a private voice channel. Empty channels are removed.</p></header><Status message={message} error={error} />
    <section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Join to Create hub" type="voice" value={value.hub_channel_id} channels={guild.channels} onChange={hub_channel_id => setValue({ ...value, hub_channel_id })} /><ChannelSelect label="Channel category" type="category" value={value.category_id} channels={guild.channels} onChange={category_id => setValue({ ...value, category_id })} /><label>Channel name template<input value={value.name_template} onChange={event => setValue({ ...value, name_template: event.target.value })} /></label><label>User limit (0 = unlimited)<input type="number" min={0} max={99} value={value.user_limit} onChange={event => setValue({ ...value, user_limit: Number(event.target.value) })} /></label><label className="flex items-center gap-2"><input type="checkbox" checked={value.enabled} onChange={event => setValue({ ...value, enabled: event.target.checked })} />Enabled</label></section>
    <section className="card"><ChannelSelect label="Control text channel" value={value.control_channel_id} channels={guild.channels} onChange={control_channel_id => setValue({ ...value, control_channel_id })} /></section>
    {sameChannel && <p className="text-sm text-red-300" role="alert">Hub and control channel must be different.</p>}
    <div className="save-bar"><button className="primary" disabled={busy || sameChannel} onClick={save}>Save</button></div>
  </>;
}
