import { Link } from 'react-router'
import type { Point } from '../lib/constellation'

type Props = {
  project: string
  projectId: number | undefined
  at: Point
  open: boolean
  onToggle: () => void
  onNewSession: () => void
}

/** A project's diamond between Alfred and its sessions; opens a small menu. */
export function ProjectHub({ project, projectId, at, open, onToggle, onNewSession }: Props) {
  return (
    <div
      style={{ left: at.x, top: at.y, transition: 'left 600ms, top 600ms' }}
      className="animate-node-in pointer-events-auto absolute z-20 -translate-x-1/2 -translate-y-1/2"
      onPointerDown={(e) => e.stopPropagation()}
    >
      <span className="pointer-events-none absolute bottom-full left-1/2 mb-1.5 -translate-x-1/2 text-[10px] tracking-[0.18em] whitespace-nowrap text-gray-400 uppercase">
        {project}
      </span>
      <button
        onClick={onToggle}
        aria-expanded={open}
        aria-label={`Projeto ${project}`}
        className={`block size-3 rotate-45 border bg-[#111113] transition hover:scale-125 ${
          open ? 'border-gray-100' : 'border-gray-400'
        }`}
      />
      {open && (
        <div className="animate-activity-in absolute top-full left-1/2 z-30 mt-2 flex w-44 -translate-x-1/2 flex-col rounded-lg border border-white/10 bg-[#111113]/95 p-1 text-xs text-gray-300 backdrop-blur">
          <button onClick={onNewSession} className="rounded px-2 py-1.5 text-left hover:bg-white/5">
            Nova sessão aqui
          </button>
          {projectId !== undefined && (
            <Link to={`/projects/${projectId}`} className="rounded px-2 py-1.5 hover:bg-white/5">
              Abrir projeto
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
