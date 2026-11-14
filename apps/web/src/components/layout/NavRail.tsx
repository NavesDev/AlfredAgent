import { NavLink } from 'react-router'
import type { Connection } from '../../hooks/useEvents'
import { Folder, LayoutGrid, Settings } from '../icons'

const LINKS = [
  { to: '/', label: 'Painel', icon: LayoutGrid },
  { to: '/projects', label: 'Projetos', icon: Folder },
  { to: '/settings', label: 'Configurações', icon: Settings },
]

const CONNECTION: Record<Connection, { label: string; dot: string }> = {
  open: { label: 'Servidor conectado', dot: 'bg-apple-green' },
  connecting: { label: 'Conectando ao servidor', dot: 'bg-apple-orange animate-pulse' },
  closed: { label: 'Servidor offline', dot: 'bg-apple-red' },
}

/** Vertical glass pill on the left (visionOS tab bar): one round icon per section. */
export function NavRail({ connection }: { connection: Connection }) {
  const status = CONNECTION[connection]
  return (
    <nav
      aria-label="Seções"
      className="glass flex flex-row items-center gap-1.5 rounded-full p-2 md:flex-col"
    >
      {LINKS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          aria-label={label}
          title={label}
          className="grid size-10 place-items-center rounded-full text-ink transition hover:bg-fill aria-[current=page]:bg-fill-on"
        >
          <Icon className="size-[18px]" />
        </NavLink>
      ))}
      <span className="mx-1 h-6 w-px bg-hairline md:mx-0 md:my-1 md:h-px md:w-6" />
      <span
        role="status"
        aria-label={status.label}
        title={status.label}
        className="grid size-10 place-items-center"
      >
        <span className={`size-2 rounded-full ${status.dot}`} />
      </span>
    </nav>
  )
}
