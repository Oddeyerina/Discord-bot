type Option = { id: string; name: string };

export default function MultiSelect({ label, value, options, onChange }: { label: string; value: string[]; options: Option[]; onChange: (value: string[]) => void }) {
  return <fieldset><legend>{label}</legend><div className="max-h-56 overflow-y-auto rounded-lg border border-slate-700 bg-slate-900 p-2 space-y-1">{options.length === 0 && <p className="text-xs text-slate-500">No options available.</p>}{options.map(option => <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm text-slate-200 hover:bg-slate-800" key={option.id}><input className="w-auto" type="checkbox" checked={value.includes(option.id)} onChange={event => onChange(event.target.checked ? [...value, option.id] : value.filter(id => id !== option.id))} />{option.name}</label>)}</div><p className="text-xs text-slate-500">{value.length} selected</p></fieldset>;
}
