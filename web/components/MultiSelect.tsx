type Option = { id: string; name: string };

export default function MultiSelect({
    label,
    value,
    options,
    onChange,
}: {
    label: string;
    value: string[];
    options: Option[];
    onChange: (value: string[]) => void;
}) {
    const toggle = (id: string) => {
        if (value.includes(id)) {
            onChange(value.filter(v => v !== id));
        } else {
            onChange([...value, id]);
        }
    };

    return (
        <div className= "space-y-1" >
        <div className="text-sm text-slate-300" > { label } </div>
            < div className = "max-h-56 overflow-y-auto rounded-lg border border-slate-700 bg-slate-900 p-2" >
            {
                options.length === 0 && (
                    <p className="text-xs text-slate-500"> No options available.</p>
        )
            }
    {
        options.map(option => (
            <label
            key= { option.id }
            className = "flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm text-slate-200 hover:bg-slate-800"
            >
            <input
              type="checkbox"
              className = "w-auto"
              checked = { value.includes(option.id) }
              onChange = {() => toggle(option.id)}
            />
        < span > { option.name } </span>
        </label>
        ))
}
</div>
    < p className = "text-xs text-slate-500" > { value.length } selected </p>
        </div>
  );
}