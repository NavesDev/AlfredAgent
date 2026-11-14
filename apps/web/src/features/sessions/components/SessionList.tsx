import { useState } from 'react'
import type { SessionView } from '../../../api/events'
import { Plus, Search } from '../../../components/icons'
import { presence, type Tone } from '../../../lib/presence'
import { SessionPhoto } from '../../../components/SessionPhoto'

const TONE_TEXT: Record<Tone, string> = {
  work: 'text-apple-teal',
  queue: 'text-apple-orange',
  error: 'text-apple-red',
  idle: 'text-ink-2',
  sleep: 'text-ink-3',
}

type Props = {
  sessions: SessionView[]
  selected: string | null
  onSelect: (name: string) => void
  onNew: () => void
}

const matches = (s: SessionView, query: string) =>
  [s.name, s.project ?? '', ...s.aliases].some((t) => t.toLowerCase().includes(query))

/** Glass panel listing the sessions, like the Settings sidebar: photo, name, project, state. */
export function SessionList({ sessions, selected, onSelect, onNew }: Props) {
  const [query, setQuery] = useState('')
  const shown = sessions.filter((s) => matches(s, query.trim().toLowerCase()))
  return (
    <section
      aria-label="Sessões"
      className="glass flex max-h-full min-h-0 flex-col gap-3 self-center rounded-panel p-3.5"
    >
      <label className="flex items-center gap-2 rounded-full bg-well px-3 py-2 text-[13px] text-ink-3">
        <Search className="size-3.5" />
        <input
          type="search"
          aria-label="Buscar sessão"
          placeholder="Buscar sessão"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-ink-3"
        />
      </label>
      <ul className="flex min-h-0 flex-col gap-0.5 overflow-y-auto">
        {shown.map((s) => {
          const { label, tone } = presence(s)
          return (
            <li key={s.name}>
              <button
                type="button"
                aria-pressed={s.name === selected}
                onClick={() => onSelect(s.name)}
                className="grid w-full grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-2.5 rounded-2xl px-2 py-1.5 text-left text-[13.5px] font-medium transition hover:bg-fill aria-pressed:bg-fill-on"
              >
                <SessionPhoto session={s} size={36} />
                <span className="min-w-0">
                  <span className="block truncate">{s.name}</span>
                  <span className="block truncate text-[11.5px] font-normal text-ink-2">
                    {s.project ?? s.label}
                  </span>
                </span>
                <span className={`text-xs whitespace-nowrap ${TONE_TEXT[tone]}`}>{label}</span>
              </button>
            </li>
          )
        })}
        {shown.length === 0 && (
          <li className="px-2 py-3 text-xs text-ink-3">
            {sessions.length ? 'Nenhuma sessão com esse nome.' : 'Nenhuma sessão ainda.'}
          </li>
        )}
      </ul>
      <button
        type="button"
        onClick={onNew}
        className="mt-auto inline-flex items-center justify-center gap-1.5 rounded-full bg-fill py-2 text-[13px] font-medium hover:bg-fill-on"
      >
        <Plus className="size-3.5" />
        Nova sessão
      </button>
    </section>
  )
}
