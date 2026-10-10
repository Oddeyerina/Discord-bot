import type { GuildData } from '@/lib/api';

export default function ChannelSelect({ label, value, onChange, channels, type = 'text' }: { label: string; value?: string | null; onChange: (value: string) => void; channels: GuildData['channels']; type?: 'text' | 'voice' | 'category' }) {
  return <label>{label}<select value={value || ''} onChange={e => onChange(e.target.value)}><option value="">Select a {type === 'category' ? 'category' : 'channel'}</option>{channels.filter(c => c.type === type).map(c => <option key={c.id} value={c.id}>{type === 'text' ? '#' : ''}{c.name}</option>)}</select></label>;
}
