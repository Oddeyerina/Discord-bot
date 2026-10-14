'use client';

import ChannelSelect from '@/components/ChannelSelect';
import MultiSelect from '@/components/MultiSelect';
import EmbedEditor from '@/components/EmbedEditor';
import Status from '@/components/Status';
import { emptyEmbed, type Embed } from '@/lib/api';
import { useConfig } from '@/hooks/useConfig';

type Config = { welcome_channel_id: string; welcome_embed: Embed; goodbye_channel_id: string; goodbye_embed: Embed; autorole_ids: string[] };
const defaults: Config = { welcome_channel_id: '', welcome_embed: { ...emptyEmbed, title: 'Welcome, {user}!' }, goodbye_channel_id: '', goodbye_embed: { ...emptyEmbed, title: 'Goodbye, {user}' }, autorole_ids: [] };

export default function WelcomePage() {
  const { value, setValue, guild, message, error, busy, save } = useConfig('/welcome/config', defaults);
  return <><header><h1 className="text-3xl font-bold">Welcome / Goodbye</h1></header><Status message={message} error={error} /><section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Welcome channel" channels={guild.channels} value={value.welcome_channel_id} onChange={welcome_channel_id => setValue({ ...value, welcome_channel_id })} /><ChannelSelect label="Goodbye channel" channels={guild.channels} value={value.goodbye_channel_id} onChange={goodbye_channel_id => setValue({ ...value, goodbye_channel_id })} /><MultiSelect label="Auto roles on join" options={guild.roles} value={value.autorole_ids || []} onChange={autorole_ids => setValue({ ...value, autorole_ids })} /></section><EmbedEditor title="Welcome embed" value={value.welcome_embed || emptyEmbed} onChange={welcome_embed => setValue({ ...value, welcome_embed })} /><EmbedEditor title="Goodbye embed" value={value.goodbye_embed || emptyEmbed} onChange={goodbye_embed => setValue({ ...value, goodbye_embed })} /><button disabled={busy} className="primary" onClick={save}>Save settings</button></>;
}

