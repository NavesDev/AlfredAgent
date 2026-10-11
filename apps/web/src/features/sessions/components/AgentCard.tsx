import { useEffect, useState } from 'react'
import type { SessionView } from '../../../api/events'
import { MiniOrb, type MiniLook } from '../../../lib/orb/MiniOrb'
import { useSessionActions } from '../hooks/useSessionActions'

const STATUS: Record<SessionView['status'], { label: string; pill: string; look: MiniLook }> = {
  busy: {
    label: 'ocupado',
    pill: 'border-amber-300/30 bg-amber-300/10 text-amber-200',
    look: { core: '#451a03', rim: '#fbbf24', active: true },
  },
  idle: {
    label: 'livre',
    pill: 'border-emerald-300/30 bg-emerald-300/10 text-emerald-200',
    look: { core: '#052e2b', rim: '#34d399', active: false },
  },
  error: {
    label: 'erro',
    pill: 'border-red-300/30 bg-red-300/10 text-red-200',
    look: { core: '#450a0a', rim: '#f87171', active: false },
  },
}

const CONFIRM_MS = 4000

const tokens = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`)

export function AgentCard({ session }: { session: SessionView }) {
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
    if (confirming) remove.mutate(session.name)
    setConfirming((v) => !v)
  }

  return (
    <article className="flex flex-col gap-1.5 rounded-xl border border-white/10 bg-white/[0.03] p-3 text-sm text-gray-300">
      <header className="flex items-center gap-2">
        <div className="size-8 shrink-0">
          <MiniOrb {...status.look} />
        </div>
        <h3 className="truncate font-medium text-gray-100">{session.name}</h3>
        <span className={`ml-auto rounded-md border px-2 py-0.5 text-[11px] ${status.pill}`}>
          {status.label}
        </span>
      </header>
      <p className="text-xs text-gray-400">
        {session.label} · {session.model} · <span className="font-mono">{session.cwd}</span>
      </p>
      {session.task && <p className="line-clamp-2 text-gray-100">“{session.task}”</p>}
      {session.activity && (
        <p className="truncate font-mono text-xs text-gray-400">{session.activity}…</p>
      )}
      <p className="text-xs text-gray-500">
        fila {session.queue} · {session.tasks_done} tarefas · {tokens(session.tokens)} tokens
      </p>
      {session.last_summary && (
        <p className="line-clamp-2 text-xs text-gray-400">último: “{session.last_summary}”</p>
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
    </article>
  )
}
