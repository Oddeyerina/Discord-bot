import type { GuildData } from '@/lib/api';

export default function EmojiSelect({ value, onChange, emojis }: { value: string; onChange: (value: string) => void; emojis: GuildData['emojis'] }) {
  const choices = emojis.map(emoji => ({ value: `<${emoji.animated ? 'a' : ''}:${emoji.name}:${emoji.id}>`, name: emoji.name }));
  return <div className="space-y-2"><label>Custom emoji<select value={choices.some(choice => choice.value === value) ? value : ''} onChange={event => onChange(event.target.value)}><option value="">Use Unicode emoji</option>{choices.map(choice => <option key={choice.value} value={choice.value}>{choice.name}</option>)}</select></label><label>Emoji or Unicode character<input value={value} onChange={event => onChange(event.target.value)} placeholder="(emoji)" /></label></div>;
}
