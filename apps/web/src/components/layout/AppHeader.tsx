import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { useConnection } from '../../hooks/useEvents'
import { Nav } from './Nav'

const CONNECTION = {
  open: { label: 'conectado', dot: 'bg-emerald-400 shadow-[0_0_8px_#34d399]' },
  connecting: { label: 'conectando', dot: 'bg-amber-400 animate-pulse' },
  closed: { label: 'offline', dot: 'bg-red-400' },
}

/**
 * The same bar on every page: brand on the left, tabs centered (the grid keeps them from
 * shifting between pages), connection plus the page's own actions on the right.
 */
export function AppHeader({ actions }: { actions?: ReactNode }) {
  const connection = CONNECTION[useConnection()]
  return (
    <header className="relative z-30 grid h-14 shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-3 border-b border-white/[0.06] bg-[#09090b]/60 px-4 backdrop-blur-md sm:px-5">
      <Link to="/" className="group flex w-fit items-center gap-2.5" aria-label="Alfred, painel">
        <span
          aria-hidden
          className="size-5 rounded-full bg-[radial-gradient(circle_at_35%_30%,#ffffff_0%,#e4e4e7_30%,#52525b_75%,#18181b_100%)] shadow-[0_0_14px_rgba(228,228,231,0.45)] transition group-hover:shadow-[0_0_20px_rgba(228,228,231,0.7)]"
        />
        <span className="hidden text-sm font-semibold tracking-[0.3em] text-gray-200 uppercase sm:inline">
          Alfred
        </span>
      </Link>
      <Nav />
      <div className="flex items-center justify-end gap-2">
        <span
          title={connection.label}
          className="flex items-center gap-2 rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-gray-400"
        >
          <span className={`size-1.5 rounded-full ${connection.dot}`} />
          <span className="hidden md:inline">{connection.label}</span>
        </span>
        {actions}
      </div>
    </header>
  )
}
