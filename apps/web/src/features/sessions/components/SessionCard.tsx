import { useEffect, useState } from 'react'
import type { SessionView } from '../../../api/events'
import { RotateCcw, Trash, X } from '../../../components/icons'
import { ModelSelect } from '../../../components/ModelSelect'
import { formatTokens } from '../../../lib/format'
import { EFFORTS, field } from '../../../lib/sessionForm'
import { contextLevel, gradientFor, initials, presence, type Tone } from '../../../lib/presence'
import type { SessionChange } from '../hooks/useSessionActions'

const CONFIRM_MS = 4000
const PILL: Record<Tone, string> = {
  work: 'bg-apple-teal/20 text-apple-teal',
  queue: 'bg-apple-orange/20 text-apple-orange',
  error: 'bg-apple-red/20 text-apple-red',
  idle: 'bg-fill text-ink-2',
  sleep: 'bg-fill text-ink-3',
}
const METER = { ok: 'bg-ink-2', warm: 'bg-apple-orange', hot: 'bg-apple-red' }
const SUBAGENT = {
  running: 'bg-apple-teal animate-pulse',
  completed: 'bg-apple-green',
  failed: 'bg-apple-red',
  stopped: 'bg-ink-3',
}

type Props = {
  session: SessionView
  onClose: () => void
  onClear: () => void
  onDelete: () => void
  onChange: (change: SessionChange) => void
  error?: string
}

/** Everything about one session, in the spirit of the "Now Playing" card. */
export function SessionCard({ session: s, onClose, onClear, onDelete, onChange, error }: Props) {
  const [confirming, setConfirming] = useState(false)
  const state = presence(s)
  const context = contextLevel(s.context_tokens, s.context_max)
  const where = [s.project, s.workspace, s.branch].filter(Boolean).join(' · ') || s.cwd
  const [from, to] = gradientFor(s.name)

  useEffect(() => {
    if (!confirming) return
    const timer = setTimeout(() => setConfirming(false), CONFIRM_MS)
    return () => clearTimeout(timer)
  }, [confirming])

  return (
    <section
      aria-label={`Sessão ${s.name}`}
      className="glass animate-activity-in flex min-h-0 flex-col gap-3.5 overflow-y-auto rounded-panel p-4"
    >
      <header className="grid grid-cols-[28px_1fr_28px] items-center text-center text-sm font-semibold">
        <span />
        <span>Sessão</span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="grid size-7 place-items-center rounded-full hover:bg-fill"
        >
          <X className="size-4" />
        </button>
      </header>

      <div className="aspect-square w-[min(100%,34vh)] shrink-0 self-center overflow-hidden rounded-[22px] bg-well">
        {s.portrait ? (
          <img src={s.portrait} alt={`Retrato de ${s.name}`} className="size-full object-cover" />
        ) : (
          <span
            aria-hidden
            style={{ background: `linear-gradient(160deg, ${from}, ${to})` }}
            className="grid size-full place-items-center text-6xl font-semibold tracking-tight text-white"
          >
            {initials(s.name)}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between gap-2.5">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold tracking-tight">{s.name}</h2>
          <p className="truncate text-xs text-ink-2">{where}</p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-[11.5px] font-semibold whitespace-nowrap ${PILL[state.tone]}`}
        >
          {state.label}
        </span>
      </div>

      <div className="flex flex-col gap-1 text-[13.5px] leading-snug">
        {s.task ? <p>{s.task}</p> : <p className="text-ink-3">Sem tarefa agora.</p>}
        {s.activity && <p className="truncate text-xs text-ink-2">{s.activity}…</p>}
        {!s.task && s.last_summary && (
          <p className="text-xs text-ink-2">Último: {s.last_summary}</p>
        )}
        {s.queue > 0 && <p className="text-xs text-ink-2">{s.queue} na fila</p>}
      </div>

      {s.last_error && (
        <div role="alert" className="rounded-2xl bg-apple-red/12 px-3 py-2 text-xs text-[#ff9a92]">
          <p className="font-semibold">Por que falhou</p>
          <p className="mt-0.5 font-mono text-[11px] break-words whitespace-pre-wrap">
            {s.last_error}
          </p>
        </div>
      )}

      <dl className="grid grid-cols-[78px_minmax(0,1fr)] items-center gap-x-3 gap-y-2.5 text-xs">
        {context && (
          <>
            <dt className="text-ink-2">Contexto</dt>
            <dd className="flex items-center gap-2.5">
              <span className="h-1 flex-1 overflow-hidden rounded-full bg-fill">
                <span
                  className={`block h-full rounded-full ${METER[context.tone]}`}
                  style={{ width: `${context.share}%` }}
                />
              </span>
              <span className="text-ink-2 tabular-nums">
                {formatTokens(s.context_tokens ?? 0)} / {formatTokens(s.context_max ?? 0)}
              </span>
            </dd>
          </>
        )}
        <dt className="text-ink-2">Modelo</dt>
        <dd className="flex gap-1.5">
          <div className="min-w-0 flex-1">
            <ModelSelect
              label="Modelo"
              compact
              value={s.model}
              onChange={(model) => model !== s.model && onChange({ model })}
            />
          </div>
          <select
            aria-label="Effort"
            value={s.effort ?? ''}
            onChange={(e) => onChange({ effort: e.target.value })}
            className={`${field} py-1 text-xs`}
          >
            <option value="">padrão</option>
            {EFFORTS.map((e) => (
              <option key={e}>{e}</option>
            ))}
          </select>
        </dd>
        {s.subagents.length > 0 && (
          <>
            <dt className="text-ink-2">Subagentes</dt>
            <dd className="flex flex-wrap gap-1.5">
              {s.subagents.map((sub) => (
                <span
                  key={sub.id}
                  title={sub.description}
                  className="inline-flex items-center gap-1.5 rounded-full bg-fill px-2.5 py-1"
                >
                  <i className={`size-1.5 rounded-full ${SUBAGENT[sub.status]}`} />
                  {sub.type}
                </span>
              ))}
            </dd>
          </>
        )}
      </dl>

      <footer className="mt-auto flex items-center justify-between gap-2 pt-1">
        <button
          type="button"
          onClick={onClear}
          aria-label="Limpar conversa"
          title="Cancela a tarefa, esvazia a fila e apaga o contexto"
          className="grid size-10 place-items-center rounded-full hover:bg-fill"
        >
          <RotateCcw className="size-[18px]" />
        </button>
        <span className="text-[11px] text-ink-3">
          {s.connected ? 'Processo aberto' : 'Retoma na próxima tarefa'}
        </span>
        {!s.protected &&
          (confirming ? (
            <button
              type="button"
              onClick={onDelete}
              className="rounded-full bg-apple-red px-3.5 py-2 text-[13px] font-semibold text-white"
            >
              Confirmar apagar
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              aria-label="Apagar sessão"
              className="grid size-10 place-items-center rounded-full text-apple-red hover:bg-apple-red/15"
            >
              <Trash className="size-[18px]" />
            </button>
          ))}
      </footer>
      {error && <p className="text-xs text-[#ff9a92]">{error}</p>}
    </section>
  )
}
