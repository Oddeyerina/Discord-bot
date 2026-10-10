import type { Embed } from '@/lib/api';

type Props = { value: Embed; onChange: (value: Embed) => void; title?: string };

export default function EmbedEditor({ value, onChange, title = 'Embed' }: Props) {
    const set = (field: keyof Embed, text: string) => onChange({ ...value, [field]: text });

    const color = value.color || '#5865F2';

    return (
        <section className= "card space-y-4" >
        <div>
        <h2 className="text-lg font-semibold" > { title } </h2>
            < p className = "text-xs text-slate-400" >
                Placeholders: { '{user}' }, { '{guild}' }, { '{membercount}' }, { '{level}' }, { '{label}' }, { '{age}' }, { '{role}' }
    </p>
        </div>

        < label > Title
        < input maxLength = { 256} value = { value.title } onChange = { e => set('title', e.target.value) } />
            </label>

            < label > Description
            < textarea rows = { 4} maxLength = { 4096} value = { value.description } onChange = { e => set('description', e.target.value) } />
                </label>

                < div className = "grid gap-4 md:grid-cols-2" >
                    <label>Color
                    < input type = "color" value = { color } onChange = { e => set('color', e.target.value) } />
                        </label>
                        < label > Footer
                        < input maxLength = { 2048} value = { value.footer } onChange = { e => set('footer', e.target.value) } />
                            </label>
                            </div>

                            < div className = "grid gap-4 md:grid-cols-2" >
                                <label>Thumbnail URL
                                    < input type = "url" value = { value.thumbnail } onChange = { e => set('thumbnail', e.target.value) } />
                                        </label>
                                        < label > Image URL
                                            < input type = "url" value = { value.image } onChange = { e => set('image', e.target.value) } />
                                                </label>
                                                </div>

    {/* Live preview */ }
    <div>
        <p className="mb-2 text-xs text-slate-400" > Preview </p>
            < div
    className = "overflow-hidden rounded-lg bg-slate-800 p-4"
    style = {{ borderLeft: `4px solid ${color}` }
}
        >
    <div className="flex gap-4" >
        <div className="min-w-0 flex-1" >
        {
            value.title && (
                <p className="mb-1 break-words font-semibold text-indigo-300">
                { value.title || '\u00A0' }
                    </p>
              )
        }
{
    value.description && (
        <p className="whitespace-pre-wrap break-words text-sm text-slate-200" >
        { value.description }
            </p>
              )
}
{
    value.image && (
        <div className="mt-3 overflow-hidden rounded" >
        {/* eslint-disable-next-line @next/next/no-img-element */ }
            < img
    src = { value.image }
    alt = "Embed image"
    className = "max-h-64 w-full object-cover"
    onError = { e => { (e.target as HTMLImageElement).style.display = 'none'; }
}
                  />
    </div>
              )}
{
    value.footer && (
        <p className="mt-3 flex items-center gap-2 text-xs text-slate-400" >
        {
            value.thumbnail && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                      src={ value.thumbnail }
    alt = ""
    className = "h-5 w-5 rounded-full object-cover"
    onError = { e => { (e.target as HTMLImageElement).style.display = 'none'; }
}
                    />
                  )}
{ value.footer }
</p>
              )}
</div>
{
    value.thumbnail && !value.footer && (
        <div className="flex-shrink-0" >
        {/* eslint-disable-next-line @next/next/no-img-element */ }
            < img
    src = { value.thumbnail }
    alt = "Thumbnail"
    className = "h-16 w-16 rounded object-cover"
    onError = { e => { (e.target as HTMLImageElement).style.display = 'none'; }
}
                />
    </div>
            )}
</div>
    </div>
    </div>
    </section>
  );
}