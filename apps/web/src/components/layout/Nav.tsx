import { useLayoutEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router'
import { Folder, LayoutGrid, Settings } from '../icons'

const LINKS = [
  { to: '/', label: 'Painel', icon: <LayoutGrid className="size-3.5" /> },
  { to: '/projects', label: 'Projetos', icon: <Folder className="size-3.5" /> },
  { to: '/settings', label: 'Configurações', icon: <Settings className="size-3.5" /> },
]

/** Pill tabs; the highlight slides to the active link (after @stealth/navbar). */
export function Nav() {
  const { pathname } = useLocation()
  const refs = useRef<(HTMLAnchorElement | null)[]>([])
  const [pill, setPill] = useState<{ left: number; width: number } | null>(null)
  const active = LINKS.findIndex((l) =>
    l.to === '/' ? pathname === '/' : pathname.startsWith(l.to),
  )

  useLayoutEffect(() => {
    const measure = () => {
      const el = refs.current[active]
      setPill(el ? { left: el.offsetLeft, width: el.offsetWidth } : null)
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [active])

  return (
    <nav
      aria-label="Principal"
      className="relative flex items-center rounded-full border border-white/10 bg-white/[0.03] p-1 text-xs shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
    >
      {pill && (
        <span
          aria-hidden
          style={{ left: pill.left, width: pill.width }}
          className="absolute inset-y-1 rounded-full bg-white/10 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)] transition-[left,width] duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
        />
      )}
      {LINKS.map((link, i) => (
        <NavLink
          key={link.to}
          ref={(el) => {
            refs.current[i] = el
          }}
          to={link.to}
          end={link.to === '/'}
          title={link.label}
          className={({ isActive }) =>
            `relative flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors ${isActive ? 'text-gray-100' : 'text-gray-400 hover:text-gray-200'}`
          }
        >
          {link.icon}
          <span className="hidden sm:inline">{link.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
