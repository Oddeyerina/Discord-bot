type Option = { id: string; name: string };

export default function MultiSelect({ label, value, options, onChange }: { label: string; value: string[]; options: Option[]; onChange: (value: string[]) => void }) {
  return <fieldset><legend>{label}</legend><div className="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-slate-700 bg-slate-800/60 p-2">{options.length === 0 && <p className="text-xs text-slate-400">No options available.</p>}{options.map(option => <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm text-slate-100 hover:bg-slate-700" key={option.id}><input className="w-auto" type="checkbox" checked={value.includes(option.id)} onChange={event => onChange(event.target.checked ? [...value, option.id] : value.filter(id => id !== option.id))} />{option.name}</label>)}</div><p className="text-xs text-slate-400">{value.length} selected</p></fieldset>;
}
