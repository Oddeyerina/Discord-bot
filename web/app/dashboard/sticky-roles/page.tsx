'use client';

import MultiSelect from '@/components/MultiSelect';
import Status from '@/components/Status';
import { useConfig } from '@/hooks/useConfig';

type Config = { excluded_role_ids: string[]; enabled: boolean };
const defaults: Config = { excluded_role_ids: [], enabled: false };

export default function StickyRolesPage() {
  const { value, setValue, guild, message, error, busy, save } = useConfig('/sticky-roles/config', defaults);
  return <><header><h1 className="text-4xl font-bold">Sticky Roles</h1><p className="text-slate-400">Restore assignable roles when a member rejoins.</p></header><Status message={message} error={error} />
    <section className="card space-y-5"><MultiSelect label="Excluded roles" options={guild.roles} value={value.excluded_role_ids} onChange={excluded_role_ids => setValue({ ...value, excluded_role_ids })} /><label className="flex items-center gap-2"><input type="checkbox" checked={value.enabled} onChange={event => setValue({ ...value, enabled: event.target.checked })} />Enabled</label></section>
    <button className="primary" disabled={busy} onClick={save}>Save</button>
  </>;
}
