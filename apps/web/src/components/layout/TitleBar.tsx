import type { ReactNode } from 'react'
import type { Connection } from '../../hooks/useEvents'
import { useMaximized } from '../../hooks/useMaximized'
import { appWindow } from '../../lib/desktop'
import { Maximize, Minus, Restore, X } from '../icons'

const DOT: Record<Connection, string> = {
  open: 'bg-apple-green',
  connecting: 'bg-apple-orange animate-pulse',
  closed: 'bg-apple-red',
}

/** The desktop window's own top bar: drags the window, title on the left, glass buttons on the right. */
export function TitleBar({ connection }: { connection: Connection }) {
  const maximized = useMaximized()
  return (
    <header
      data-tauri-drag-region
      className="relative flex h-10 shrink-0 items-center justify-between px-3 select-none"
    >
      <div className="pointer-events-none flex items-center gap-2 pl-1 text-[13px] font-semibold">
        <span className={`size-2 rounded-full ${DOT[connection]}`} />
        <span className="font-display text-[19px] leading-none font-normal italic [font-variation-settings:'opsz'_72]">
          Alfred
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <WindowButton label="Minimizar" onClick={() => appWindow().minimize()}>
          <Minus className="size-3.5" />
        </WindowButton>
        <WindowButton
          label={maximized ? 'Restaurar' : 'Maximizar'}
          onClick={() => appWindow().toggleMaximize()}
        >
          {maximized ? <Restore className="size-3.5" /> : <Maximize className="size-3" />}
        </WindowButton>
        <WindowButton label="Fechar" onClick={() => appWindow().close()} danger>
          <X className="size-3.5" />
        </WindowButton>
      </div>
    </header>
  )
}

type ButtonProps = { label: string; onClick: () => void; danger?: boolean; children: ReactNode }

function WindowButton({ label, onClick, danger, children }: ButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`glass grid size-7 place-items-center rounded-full text-ink transition ${
        danger ? 'hover:bg-apple-red/80' : 'hover:bg-fill-on'
      }`}
    >
      {children}
    </button>
  )
}
