import type { ComponentType, SVGProps } from 'react'
import { BarChart, Download, Gauge, Monitor, Plug, Sparkle } from '../../../components/icons'
import { SECTIONS, type SectionId } from '../lib/sections'

const ICON: Record<SectionId, ComponentType<SVGProps<SVGSVGElement>>> = {
  uso: BarChart,
  geral: Monitor,
  modelos: Sparkle,
  sessoes: Gauge,
  mcps: Plug,
  atualizacoes: Download,
}

type Props = { current: SectionId; onSelect: (id: SectionId) => void }

/** The settings sidebar: a coloured square icon and a name per section, like the iOS Settings. */
export function SettingsNav({ current, onSelect }: Props) {
  return (
    <nav aria-label="Seções das configurações">
      <ul className="flex flex-col gap-0.5">
        {SECTIONS.map(({ id, label, color }) => {
          const Icon = ICON[id]
          return (
            <li key={id}>
              <a
                href={`#${id}`}
                aria-current={id === current ? 'page' : undefined}
                onClick={() => onSelect(id)}
                className="flex items-center gap-3 rounded-[14px] p-2 text-sm font-medium transition hover:bg-fill aria-[current=page]:bg-fill-on"
              >
                <span className={`grid size-7 place-items-center rounded-lg text-white ${color}`}>
                  <Icon className="size-[15px]" />
                </span>
                {label}
              </a>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
