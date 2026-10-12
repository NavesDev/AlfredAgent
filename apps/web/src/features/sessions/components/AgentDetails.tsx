import { useEffect, useState, type CSSProperties } from 'react'
import type { SessionView } from '../../../api/events'
import { useSessionActions } from '../hooks/useSessionActions'
import { formatTokens, STATUS } from '../lib/status'

const CONFIRM_MS = 4000

type Props = { session: SessionView; style: CSSProperties; onClose: () => void }

/** What a node opens: everything about the session, plus clear and delete. */
export function AgentDetails({ session, style, onClose }: Props) {
  const { clear, remove } = useSessionActions()
  const [confirming, setConfirming] = useState(false)
  const status = STATUS[session.status]
  const error = clear.error ?? remove.error

  useEffect(() => {
    if (!confirming) return
    const timer = setTimeout(() => setConfirming(false), CONFIRM_MS)
    return () => clearTimeout(timer)
  }, [confirming])

  const onDelete = () => {
    if (confirming) remove.mutate(session.name, { onSuccess: onClose })
    setConfirming((v) => !v)
  }

  return (
    <div
      role="dialog"
      aria-label={`Sessão ${session.name}`}
      style={style}
      onPointerDown={(e) => e.stopPropagation()}
      className="animate-activity-in pointer-events-auto absolute z-30 flex w-72 flex-col gap-1.5 rounded-xl border border-white/10 bg-[#0a0f1c]/95 p-3 text-sm text-gray-300 backdrop-blur"
    >
      <header className="flex items-center gap-2">
        <h3 className="truncate font-medium text-gray-100">{session.name}</h3>
        <span className={`rounded-md border px-2 py-0.5 text-[11px] ${status.pill}`}>
          {status.label}
        </span>
        <button
          onClick={onClose}
          aria-label="Fechar"
          className="ml-auto rounded px-1.5 text-gray-500 hover:text-gray-200"
        >
          ×
        </button>
      </header>
      <p className="text-xs text-gray-400">
        {session.label} · {session.model} · <span className="font-mono">{session.cwd}</span>
      </p>
      {session.task && <p className="text-gray-100">“{session.task}”</p>}
      {session.activity && (
        <p className="truncate font-mono text-xs text-gray-400">{session.activity}…</p>
      )}
      <p className="text-xs text-gray-500">
        fila {session.queue} · {session.tasks_done} tarefas · {formatTokens(session.tokens)} tokens
      </p>
      {session.last_summary && (
        <p className="text-xs text-gray-400">último: “{session.last_summary}”</p>
      )}
      <footer className="mt-1 flex gap-2">
        <button
          onClick={() => clear.mutate(session.name)}
          disabled={clear.isPending}
          title="Cancela a tarefa, esvazia a fila e apaga o contexto"
          className="rounded-md border border-white/10 px-2.5 py-1 text-xs hover:bg-white/5"
        >
          Limpar
        </button>
        {!session.protected && (
          <button
            onClick={onDelete}
            disabled={remove.isPending}
            className={`rounded-md border px-2.5 py-1 text-xs ${
              confirming
                ? 'border-red-400/50 bg-red-400/15 text-red-200'
                : 'border-white/10 text-red-300 hover:bg-red-400/10'
            }`}
          >
            {confirming ? 'Confirmar apagar' : 'Apagar'}
          </button>
        )}
      </footer>
      {error && <p className="text-xs text-red-300">{error.message}</p>}
    </div>
  )
}
