'use client';

import ChannelSelect from '@/components/ChannelSelect';
import RoleSelect from '@/components/RoleSelect';
import EmbedEditor from '@/components/EmbedEditor';
import Status from '@/components/Status';
import { api, emptyEmbed, type Embed } from '@/lib/api';
import { useConfig } from '@/hooks/useConfig';
import { useState } from 'react';

type Config = { rules_channel_id: string; rules_embed: Embed; button_label: string; verified_role_id: string; enabled: boolean; rules_message_id?: string | null };
const defaults: Config = { rules_channel_id: '', rules_embed: { ...emptyEmbed, title: 'Server rules' }, button_label: 'I agree to the rules', verified_role_id: '', enabled: false };

export default function VerificationPage() {
  const { value, setValue, guild, message, error, busy, save } = useConfig('/verification/config', defaults);
  const [publishMessage, setPublishMessage] = useState('');
  async function publish(resend: boolean) {
    try { await api('/verification/config', { method: 'PUT', body: JSON.stringify(value) }); const row = await api<{ task_id: number }>(`/verification/post?resend=${resend}`, { method: 'POST' }); setPublishMessage(`Rules task #${row.task_id} queued.`); }
    catch (cause) { setPublishMessage((cause as Error).message); }
  }
  return <><h1 className="text-4xl font-bold">Rules verification</h1><Status message={message || publishMessage} error={error} />
    <section className="card grid gap-4 md:grid-cols-2"><ChannelSelect label="Rules channel" channels={guild.channels} value={value.rules_channel_id} onChange={rules_channel_id => setValue({ ...value, rules_channel_id })} /><RoleSelect label="Verified role" roles={guild.roles} value={value.verified_role_id} onChange={verified_role_id => setValue({ ...value, verified_role_id })} /><label>Button label<input maxLength={80} value={value.button_label} onChange={e => setValue({ ...value, button_label: e.target.value })} /></label><label className="flex items-center gap-2"><input type="checkbox" checked={value.enabled} onChange={e => setValue({ ...value, enabled: e.target.checked })} />Enabled</label></section>
    <EmbedEditor title="Rules embed" value={value.rules_embed || emptyEmbed} onChange={rules_embed => setValue({ ...value, rules_embed })} />
    <div className="save-bar"><button className="secondary" disabled={busy} onClick={save}>Save</button><button className="primary" disabled={busy} onClick={() => publish(false)}>Post / Update Rules</button><button className="secondary" disabled={busy} onClick={() => publish(true)}>Resend Rules</button></div>
  </>;
}
