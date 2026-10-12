import type { SessionView } from '../../../api/events'
import { useButler } from '../hooks/useButler'
import type { Point } from '../lib/constellation'
import { STATUS } from '../lib/status'
import { Butler } from './butler/Butler'
import { SubagentDots } from './SubagentDots'

type Props = {
  session: SessionView
  at: Point
  open: boolean
  lines: string[]
  onToggle: () => void
}

const LINE: Record<string, string> = {
  sleeping: 'cochilando',
  exploring: 'explorando',
  editing: 'editando',
  running: 'rodando',
  delegating: 'chamando subagente',
  done: 'terminou',
  error: 'falhou na última tarefa',
  waiting: 'aguardando você',
}

/** An implementation session: the pixel butler, its subagents and a terminal on hover. */
export function ButlerNode({ session, at, open, lines, onToggle }: Props) {
  const state = useButler(session)
  const detail = session.status === 'busy' ? session.activity : null
  const line = session.waiting
    ? 'na fila por uma vaga'
    : `${LINE[state]}${detail ? ` · ${detail}` : ''}`

  return (
    <div
      style={{ left: at.x, top: at.y, transition: 'left 600ms, top 600ms' }}
      className="group animate-node-in pointer-events-auto absolute z-20 -translate-x-1/2 -translate-y-1/2"
    >
      <button
        onClick={onToggle}
        onPointerDown={(e) => e.stopPropagation()}
        aria-expanded={open}
        aria-label={`Sessão ${session.name}, ${LINE[state]}`}
        className={`relative block rounded-md transition ${open ? 'ring-2 ring-white/15' : ''}`}
      >
        <Butler state={state} className="h-10 w-11 transition-transform group-hover:scale-110" />
      </button>
      <SubagentDots subagents={session.subagents} />
      <span className="pointer-events-none absolute top-full left-1/2 flex w-44 -translate-x-1/2 flex-col items-center text-center">
        <span className={`text-xs tracking-wide ${STATUS[session.status].name}`}>
          {session.name}
        </span>
        {session.workspace && (
          <span className="text-[10px] text-gray-500">
            {session.workspace}
            {session.branch ? ` · ⎇ ${session.branch}` : ''}
          </span>
        )}
        <span className="max-w-full truncate font-mono text-[11px] text-gray-400">{line}</span>
      </span>
      {lines.length > 0 && !open && (
        <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 w-60 -translate-x-1/2 overflow-hidden rounded-md border border-white/10 bg-[#0c0c0e]/95 opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
          <div className="flex h-3 items-center gap-1 border-b border-white/5 pl-1.5">
            {[0, 1, 2].map((i) => (
              <i key={i} className="size-1 rounded-full bg-white/15" />
            ))}
          </div>
          <pre className="px-2 py-1 font-mono text-[10px] leading-4 text-gray-400">
            {lines.map((l, i) => (
              <div key={i} className={`truncate ${i === lines.length - 1 ? 'text-gray-100' : ''}`}>
                {l}
              </div>
            ))}
          </pre>
        </div>
      )}
    </div>
  )
}
