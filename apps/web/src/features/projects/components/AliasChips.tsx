import { useState } from 'react'
import { Plus, X } from '../../../components/icons'

type Props = { aliases: string[]; onChange: (aliases: string[]) => void; pending?: boolean }

/** Spoken names as chips: tap the x to drop one, "+ Apelido" to add one. */
export function AliasChips({ aliases, onChange, pending }: Props) {
  const [draft, setDraft] = useState<string | null>(null)

  const add = () => {
    const alias = draft?.trim() ?? ''
    const known = aliases.some((a) => a.toLowerCase() === alias.toLowerCase())
    if (alias && !known) onChange([...aliases, alias])
    setDraft(null)
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {aliases.map((a) => (
        <span
          key={a}
          className="inline-flex items-center gap-1 rounded-full bg-fill py-1 pr-1.5 pl-3 text-[12.5px]"
        >
          {a}
          <button
            type="button"
            onClick={() => onChange(aliases.filter((x) => x !== a))}
            disabled={pending}
            aria-label={`Tirar apelido ${a}`}
            className="grid size-4 place-items-center rounded-full text-ink-2 hover:bg-fill-on hover:text-ink"
          >
            <X className="size-3" />
          </button>
        </span>
      ))}
      {draft === null ? (
        <button
          type="button"
          onClick={() => setDraft('')}
          disabled={pending}
          className="inline-flex items-center gap-1 rounded-full bg-apple-blue/15 px-3 py-1 text-[12.5px] text-apple-blue"
        >
          <Plus className="size-3" />
          Apelido
        </button>
      ) : (
        <input
          aria-label="Novo apelido"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={add}
          onKeyDown={(e) => {
            if (e.key === 'Enter') add()
            if (e.key === 'Escape') setDraft(null)
          }}
          placeholder="como você fala"
          className="w-32 rounded-full bg-well px-3 py-1 text-[12.5px] outline-none focus:ring-2 focus:ring-apple-blue/60"
          autoFocus
        />
      )}
    </div>
  )
}
