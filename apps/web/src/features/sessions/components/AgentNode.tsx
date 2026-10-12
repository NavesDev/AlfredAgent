import type { SessionView } from '../../../api/events'
import { MiniOrb } from '../../../lib/orb/MiniOrb'
import type { Point } from '../lib/constellation'
import { STATUS } from '../lib/status'

type Props = { session: SessionView; at: Point; open: boolean; onToggle: () => void }

/** An agent as a small orb with a floating label: name, then what it is doing. */
export function AgentNode({ session, at, open, onToggle }: Props) {
  const status = STATUS[session.status]
  const busy = session.status === 'busy'
  const line = busy
    ? (session.activity ?? session.task ?? 'trabalhando')
    : session.status === 'error'
      ? 'falhou na última tarefa'
      : `${status.label} · ${session.model}`

  return (
    <button
      onClick={onToggle}
      onPointerDown={(e) => e.stopPropagation()}
      aria-expanded={open}
      aria-label={`Sessão ${session.name}, ${status.label}`}
      style={{ left: at.x, top: at.y, transition: 'left 600ms, top 600ms' }}
      className="animate-node-in pointer-events-auto absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
    >
      <span
        className={`relative block transition-[width,height] duration-500 ${busy ? 'size-16' : 'size-12'}`}
      >
        <span
          aria-hidden="true"
          style={{ background: `radial-gradient(circle, ${status.color}55 0%, transparent 70%)` }}
          className={`absolute -inset-3 rounded-full transition-opacity ${
            busy || open ? 'opacity-100' : 'opacity-50'
          } ${busy ? 'animate-pulse' : ''}`}
        />
        <MiniOrb {...status.orb} />
      </span>
      <span className="pointer-events-none absolute top-full mt-1 flex w-36 flex-col items-center text-center">
        <span className={`text-xs font-medium tracking-wide ${status.text}`}>{session.name}</span>
        <span
          className={`max-w-full truncate text-[11px] ${busy ? 'font-mono text-gray-300' : 'text-gray-500'}`}
        >
          {line}
        </span>
      </span>
    </button>
  )
}
