import { NavLink } from 'react-router'

const LINKS = [
  { to: '/', label: 'Painel' },
  { to: '/projects', label: 'Projetos' },
  { to: '/settings', label: 'Configurações' },
]

export function Nav() {
  return (
    <nav className="flex items-center gap-1 text-xs">
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.to === '/'}
          className={({ isActive }) =>
            `rounded-md px-2.5 py-1.5 ${isActive ? 'bg-white/10 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  )
}
