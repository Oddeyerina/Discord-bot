'use client';

import ChannelSelect from '@/components/ChannelSelect';
import RoleSelect from '@/components/RoleSelect';
import EmbedEditor from '@/components/EmbedEditor';
import EmojiSelect from '@/components/EmojiSelect';
import Status from '@/components/Status';
import { emptyEmbed, type Embed } from '@/lib/api';
import { useConfig } from '@/hooks/useConfig';

type Mapping = { emoji: string; role_id: string };
type Config = { channel_id: string; embed: Embed; style: 'reaction' | 'select'; extra_config: object; mappings: Mapping[] };
const defaults: Config = { channel_id: '', embed: { ...emptyEmbed, title: 'Choose your roles' }, style: 'reaction', extra_config: {}, mappings: [] };

export default function ReactionRolesPage() {
  const { value, setValue, guild, message, error, busy, save, publish } = useConfig('/reaction-roles/config', defaults);
  const change = (index: number, patch: Partial<Mapping>) => setValue({ ...value, mappings: value.mappings.map((m, i) => i === index ? { ...m, ...patch } : m) });
  return <><header><h1 className="text-3xl font-bold">Reaction roles</h1></header><Status message={message} error={error} /><section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Panel channel" channels={guild.channels} value={value.channel_id} onChange={channel_id => setValue({ ...value, channel_id })} /><label>Style<select value={value.style} onChange={e => setValue({ ...value, style: e.target.value as Config['style'] })}><option value="reaction">Reactions</option><option value="select">Select menu</option></select></label></section><EmbedEditor value={value.embed || emptyEmbed} onChange={embed => setValue({ ...value, embed })} /><section className="space-y-4"><div className="flex justify-between"><h2 className="text-xl font-semibold">Mappings</h2><button className="secondary" onClick={() => setValue({ ...value, mappings: [...value.mappings, { emoji: '', role_id: '' }] })}>Add mapping</button></div>{value.mappings.map((mapping, index) => <div className="card grid items-end gap-4 md:grid-cols-[1fr_2fr_auto]" key={index}><EmojiSelect value={mapping.emoji} onChange={emoji => change(index, { emoji })} emojis={guild.emojis} /><RoleSelect label="Role" roles={guild.roles} value={mapping.role_id} onChange={role_id => change(index, { role_id })} /><button className="secondary" onClick={() => setValue({ ...value, mappings: value.mappings.filter((_, i) => i !== index) })}>Remove</button></div>)}</section><div className="flex gap-3"><button className="secondary" disabled={busy} onClick={save}>Save</button><button className="primary" disabled={busy || !value.channel_id} onClick={() => publish('reactionroles')}>Post / Update Panel</button></div></>;
}
