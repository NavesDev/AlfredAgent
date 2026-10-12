import { useEffect, useState, type CSSProperties } from 'react'
import type { SessionView } from '../../../api/events'
import { EFFORTS, field } from '../../../lib/sessionForm'
import { ModelSelect } from '../../../components/ModelSelect'
import { useLook } from '../hooks/useLook'
import { useSessionActions } from '../hooks/useSessionActions'
import { formatTokens, STATUS } from '../lib/status'
import { AgentFigure } from './AgentFigure'

const CONFIRM_MS = 4000
const SUBAGENT = { running: 'rodando', completed: 'feito', failed: 'falhou', stopped: 'parado' }

type Props = { session: SessionView; style: CSSProperties; onClose: () => void }

/** What a node opens: everything about the session, plus clear and delete. */
export function AgentDetails({ session, style, onClose }: Props) {
  const { clear, remove, change } = useSessionActions()
  const look = useLook(session)
  const [confirming, setConfirming] = useState(false)
  const status = STATUS[session.status]
  const error = clear.error ?? remove.error ?? change.error

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
      <AgentFigure look={look} className="mx-auto h-24 w-28" />
      <p className="text-xs text-gray-400">
        {session.label}
        {session.project && (
          <>
            {' '}
            · {session.project} / {session.workspace}
            {session.branch && <span className="text-gray-500"> ⎇ {session.branch}</span>}
          </>
        )}
        {' · '}
        <span className="font-mono">{session.cwd}</span>
      </p>
      <div className="flex gap-1.5">
        <div className="min-w-0 flex-1">
          <ModelSelect
            label="Modelo"
            compact
            value={session.model}
            onChange={(model) =>
              model !== session.model && change.mutate({ name: session.name, model })
            }
          />
        </div>
        <select
          aria-label="Effort"
          value={session.effort ?? ''}
          onChange={(e) => change.mutate({ name: session.name, effort: e.target.value })}
          className={`${field} py-1 text-xs`}
        >
          <option value="">effort padrão</option>
          {EFFORTS.map((e) => (
            <option key={e}>{e}</option>
          ))}
        </select>
      </div>
      <p className="text-[11px] text-gray-500">
        {session.connected ? 'processo aberto' : 'dormindo (retoma na próxima tarefa)'}
        {session.waiting && ' · esperando vaga'}
      </p>
      {session.task && <p className="text-gray-100">“{session.task}”</p>}
      {session.activity && (
        <p className="truncate font-mono text-xs text-gray-400">{session.activity}…</p>
      )}
      <p className="text-xs text-gray-500">
        fila {session.queue} · {session.tasks_done} tarefas · {formatTokens(session.tokens)} tokens
      </p>
      {session.subagents.length > 0 && (
        <ul className="flex flex-col gap-0.5 border-l border-white/10 pl-2 text-xs">
          {session.subagents.map((sub) => (
            <li
              key={sub.id}
              className={sub.status === 'running' ? 'text-gray-200' : 'text-gray-500'}
            >
              <span className="font-mono">{sub.type}</span> · {sub.description}
              {sub.last_tool && <span className="font-mono text-gray-500"> · {sub.last_tool}</span>}
              {sub.status !== 'running' && <span> · {SUBAGENT[sub.status]}</span>}
            </li>
          ))}
        </ul>
      )}
      {session.last_error && (
        <div
          role="alert"
          className="rounded-md border border-red-300/25 bg-red-400/10 px-2 py-1.5 text-xs text-red-200"
        >
          <p className="font-medium">Por que falhou</p>
          <p className="mt-0.5 font-mono text-[11px] break-words whitespace-pre-wrap text-red-200/80">
            {session.last_error}
          </p>
        </div>
      )}
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
