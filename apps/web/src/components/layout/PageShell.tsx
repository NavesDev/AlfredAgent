import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { ChevronLeft } from '../icons'
import { AppShell } from './AppShell'

type Props = {
  /** Left out when the side panel already names the page. */
  title?: ReactNode
  /** Small line under the title (counts, aliases…). */
  subtitle?: ReactNode
  /** Buttons aligned with the title. */
  actions?: ReactNode
  back?: { to: string; label: string }
  /** Left glass panel (project header, settings sections); stacks above on phones. */
  aside?: ReactNode
  children: ReactNode
}

/** A page of the panel: an optional side panel and a scrolling glass panel with the content. */
export function PageShell({ title, subtitle, actions, back, aside, children }: Props) {
  return (
    <AppShell>
      <div className="flex h-full flex-col gap-4 md:flex-row md:gap-6">
        {aside && (
          <aside className="glass flex shrink-0 flex-col gap-5 overflow-y-auto rounded-panel p-5 md:w-[min(320px,30%)]">
            {back && <BackLink {...back} />}
            {aside}
          </aside>
        )}
        <main className="glass flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto rounded-panel">
          <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-5 md:p-7">
            {(title || actions || subtitle || (back && !aside)) && (
              <header className="flex flex-col gap-1">
                {back && !aside && <BackLink {...back} />}
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <h1 className="text-[26px] leading-tight font-bold tracking-tight">{title}</h1>
                  {actions && <div className="flex items-center gap-2">{actions}</div>}
                </div>
                {subtitle && <div className="text-sm text-ink-2">{subtitle}</div>}
              </header>
            )}
            {children}
          </div>
        </main>
      </div>
    </AppShell>
  )
}

function BackLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="inline-flex w-fit items-center gap-0.5 text-sm text-apple-blue hover:opacity-80"
    >
      <ChevronLeft className="size-4" />
      {label}
    </Link>
  )
}

const pill =
  'inline-flex items-center justify-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-medium transition disabled:opacity-40'
export const card = 'rounded-card bg-well p-4'
export const button = `${pill} bg-fill text-ink hover:bg-fill-on`
export const primaryButton = `${pill} bg-ink text-[#111] hover:bg-white`
export const dangerButton = `${pill} bg-apple-red/15 text-[#ff6961] hover:bg-apple-red/25`
