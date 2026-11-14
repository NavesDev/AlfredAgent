import { useState } from 'react'
import { field } from '../../../lib/sessionForm'

export const MAX_DESCRIPTION = 200

type Props = {
  value: string
  label: string
  onSave: (text: string) => void
  pending?: boolean
  error?: string
}

/** A short description that reads as plain text and turns into an input on click. */
export function Description({ value, label, onSave, pending, error }: Props) {
  const [draft, setDraft] = useState<string | null>(null)

  const save = () => {
    if (draft !== null && draft.trim() !== value) onSave(draft.trim())
    setDraft(null)
  }

  if (draft === null)
    return (
      <span className="flex flex-col gap-0.5">
        <button
          type="button"
          onClick={() => setDraft(value)}
          aria-label={`Editar ${label}`}
          className={`w-fit text-left text-xs transition hover:text-ink ${value ? 'text-ink-2' : 'text-apple-blue'}`}
        >
          {pending ? 'Salvando…' : value || 'Adicionar descrição'}
        </button>
        {error && <span className="text-xs text-[#ff9a92]">{error}</span>}
      </span>
    )

  return (
    <span className="flex items-center gap-2">
      <input
        aria-label={label}
        value={draft}
        maxLength={MAX_DESCRIPTION}
        placeholder="do que se trata, em uma frase"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => {
          if (e.key === 'Enter') save()
          if (e.key === 'Escape') setDraft(null)
        }}
        className={`${field} min-w-0 flex-1 text-xs`}
        autoFocus
      />
      <span className="text-[11px] text-ink-3 tabular-nums">
        {draft.length}/{MAX_DESCRIPTION}
      </span>
    </span>
  )
}
