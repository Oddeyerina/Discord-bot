import type { GuildData } from '@/lib/api';

export default function RoleSelect({ label, value, onChange, roles }: { label: string; value?: string | null; onChange: (value: string) => void; roles: GuildData['roles'] }) {
  return <label>{label}<select value={value || ''} onChange={e => onChange(e.target.value)}><option value="">Select a role</option>{roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label>;
}
