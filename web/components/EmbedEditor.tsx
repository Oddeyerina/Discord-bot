'use client';

import { useEffect, useState } from 'react';
import { api, type Embed, type GuildData } from '@/lib/api';

type Props = { value: Embed; onChange: (value: Embed) => void; title?: string };
let guildDataRequest: Promise<GuildData> | null = null;

function PreviewText({ text, guild }: { text: string; guild: GuildData | null }) {
  const tokens = text.split(/(<#[0-9]+>|<@!?[0-9]+>|<@&[0-9]+>)/g);
  return <>{tokens.map((token, index) => {
    const channelId = token.match(/^<#([0-9]+)>$/)?.[1];
    const roleId = token.match(/^<@&([0-9]+)>$/)?.[1];
    const userId = token.match(/^<@!?([0-9]+)>$/)?.[1];
    if (!channelId && !roleId && !userId) return <span key={index}>{token}</span>;
    const channel = channelId && guild?.channels.find(item => item.id === channelId);
    const role = roleId && guild?.roles.find(item => item.id === roleId);
    const resolved = Boolean(channel || role);
    const label = channel ? `#${channel.name}` : role ? `@${role.name}` : channelId ? `#${channelId}` : `@${roleId || userId}`;
    return <span key={index} title={resolved ? undefined : 'Mention could not be resolved'}
      className={`mx-0.5 inline-flex rounded px-1.5 py-0.5 text-xs font-medium ${resolved ? 'bg-slate-700/80 text-slate-100' : 'bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/30'}`}>{label}</span>;
  })}</>;
}

export default function EmbedEditor({ value, onChange, title = 'Embed' }: Props) {
  const [guild, setGuild] = useState<GuildData | null>(null);
  useEffect(() => {
    guildDataRequest ||= api<GuildData>('/guild/data').catch(error => { guildDataRequest = null; throw error; });
    guildDataRequest.then(setGuild).catch(() => { /* Preview remains usable without guild names. */ });
  }, []);
  const set = (field: keyof Embed, text: string) => onChange({ ...value, [field]: text });
  const color = value.color || '#5865F2';
  return <section className="card space-y-5">
    <h2 className="text-xl font-semibold">{title}</h2>
    <div className="grid gap-6 md:grid-cols-2">
      <div className="space-y-5">
        <label>Title<input maxLength={256} value={value.title || ''} onChange={event => set('title', event.target.value)} /></label>
        <label>Description<textarea rows={8} maxLength={4096} value={value.description || ''} onChange={event => set('description', event.target.value)} /></label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label>Color<input type="color" value={color} onChange={event => set('color', event.target.value)} /></label>
          <label>Footer<input maxLength={2048} value={value.footer || ''} onChange={event => set('footer', event.target.value)} /></label>
        </div>
        <label>Thumbnail URL<input type="url" value={value.thumbnail || ''} onChange={event => set('thumbnail', event.target.value)} /></label>
        <label>Image URL<input type="url" value={value.image || ''} onChange={event => set('image', event.target.value)} /></label>
      </div>
      <div className="min-w-0"><p className="mb-2 text-sm text-slate-400">Preview</p>
        <div className="overflow-hidden rounded-lg bg-slate-800 p-4" style={{ borderLeft: `4px solid ${color}` }}>
          <div className="flex gap-4"><div className="min-w-0 flex-1">
            {value.title && <p className="mb-1 break-words font-semibold text-indigo-200"><PreviewText text={value.title} guild={guild} /></p>}
            {value.description && <p className="whitespace-pre-wrap break-words text-sm text-slate-100"><PreviewText text={value.description} guild={guild} /></p>}
            {value.image && <div className="mt-3 overflow-hidden rounded">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={value.image} alt="Embed image" className="max-h-64 w-full object-cover" onError={event => { (event.target as HTMLImageElement).style.display = 'none'; }} />
            </div>}
            {value.footer && <p className="mt-3 whitespace-pre-wrap break-words text-xs text-slate-400"><PreviewText text={value.footer} guild={guild} /></p>}
          </div>
          {value.thumbnail && <div className="shrink-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={value.thumbnail} alt="Thumbnail" className="h-16 w-16 rounded object-cover" onError={event => { (event.target as HTMLImageElement).style.display = 'none'; }} />
          </div>}</div>
        </div>
      </div>
    </div>
    <p className="rounded-lg bg-slate-800/40 px-4 py-3 text-xs text-slate-400">Placeholders: {'{user}'}, {'{guild}'}, {'{membercount}'}, {'{level}'}, {'{label}'}, {'{age}'}, {'{role}'}. The preview highlights mentions it cannot resolve; saved embed text is unchanged.</p>
  </section>;
}
