import type { SessionView } from '../../../api/events'
import type { Point } from '../lib/constellation'
import { STATUS } from '../lib/status'

type Props = { session: SessionView; at: Point; open: boolean; onToggle: () => void }

/** An agent as a small dot with a floating label: name, then what it is doing. */
export function AgentNode({ session, at, open, onToggle }: Props) {
  const status = STATUS[session.status]
  const busy = session.status === 'busy'
  const line = busy
    ? (session.activity ?? session.task ?? 'trabalhando')
    : session.status === 'error'
      ? 'falhou na última tarefa'
      : status.label

  return (
    <button
      onClick={onToggle}
      onPointerDown={(e) => e.stopPropagation()}
      aria-expanded={open}
      aria-label={`Sessão ${session.name}, ${status.label}`}
      style={{ left: at.x, top: at.y, transition: 'left 600ms, top 600ms' }}
      className="group animate-node-in pointer-events-auto absolute z-20 grid size-8 -translate-x-1/2 -translate-y-1/2 place-items-center"
    >
      {busy && (
        <span
          aria-hidden="true"
          className="animate-breathe absolute size-6 rounded-full bg-gray-100/15"
        />
      )}
      <span
        aria-hidden="true"
        className={`relative rounded-full transition-all duration-500 group-hover:scale-125 ${status.dot} ${
          open ? 'ring-4 ring-white/10' : ''
        }`}
      />
      <span className="pointer-events-none absolute top-full flex w-36 flex-col items-center text-center">
        <span className={`text-xs tracking-wide ${status.name}`}>{session.name}</span>
        <span
          className={`max-w-full truncate text-[11px] ${busy ? 'font-mono text-gray-400' : 'text-gray-600'}`}
        >
          {line}
        </span>
      </span>
    </button>
  )
}
