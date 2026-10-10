import type { Embed } from '@/lib/api';

type Props = { value: Embed; onChange: (value: Embed) => void; title?: string };

export default function EmbedEditor({ value, onChange, title = 'Embed' }: Props) {
  const set = (field: keyof Embed, text: string) => onChange({ ...value, [field]: text });
  return <section className="card space-y-4">
    <div><h2 className="text-lg font-semibold">{title}</h2><p className="text-xs text-slate-400">Placeholders: {'{user}'}, {'{guild}'}, {'{membercount}'}, {'{level}'}, {'{label}'}, {'{age}'}</p></div>
    <label>Title<input maxLength={256} value={value.title} onChange={e => set('title', e.target.value)} /></label>
    <label>Description<textarea rows={4} maxLength={4096} value={value.description} onChange={e => set('description', e.target.value)} /></label>
    <div className="grid gap-4 md:grid-cols-2"><label>Color<input type="color" value={value.color} onChange={e => set('color', e.target.value)} /></label><label>Footer<input maxLength={2048} value={value.footer} onChange={e => set('footer', e.target.value)} /></label></div>
    <div className="grid gap-4 md:grid-cols-2"><label>Thumbnail URL<input type="url" value={value.thumbnail} onChange={e => set('thumbnail', e.target.value)} /></label><label>Image URL<input type="url" value={value.image} onChange={e => set('image', e.target.value)} /></label></div>
  </section>;
}
