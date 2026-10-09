import type { GuildData } from '@/lib/api';

export default function ChannelSelect({ label, value, onChange, channels }: { label: string; value?: string | null; onChange: (value: string) => void; channels: GuildData['channels'] }) {
  return <label>{label}<select value={value || ''} onChange={e => onChange(e.target.value)}><option value="">Select a channel</option>{channels.map(c => <option key={c.id} value={c.id}>#{c.name}</option>)}</select></label>;
}
