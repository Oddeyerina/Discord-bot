type Option = { id: string; name: string };

export default function MultiSelect({ label, value, options, onChange }: { label: string; value: string[]; options: Option[]; onChange: (value: string[]) => void }) {
  return <label>{label}<select multiple size={Math.min(5, Math.max(2, options.length))} value={value} onChange={event => onChange(Array.from(event.target.selectedOptions, option => option.value))}>{options.map(option => <option key={option.id} value={option.id}>{option.name}</option>)}</select><span className="text-xs text-slate-500">Ctrl or Command click to select multiple.</span></label>;
}
