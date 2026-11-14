import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { ChevronLeft } from '../icons'
import { AppHeader } from './AppHeader'

type Props = {
  title: ReactNode
  /** Small line under the title (counts, aliases…). */
  subtitle?: ReactNode
  /** Buttons aligned with the title. */
  actions?: ReactNode
  back?: { to: string; label: string }
  children: ReactNode
}

/** Header with the app name and navigation, then a scrolling content column. */
export function PageShell({ title, subtitle, actions, back, children }: Props) {
  return (
    <div className="flex h-full flex-col bg-[radial-gradient(ellipse_at_top,#161618_0%,#09090b_65%)]">
      <AppHeader />
      <main className="min-h-0 flex-1 overflow-y-auto px-4 pt-6 pb-10 sm:px-5">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          <div className="flex flex-col gap-1">
            {back && (
              <Link
                to={back.to}
                className="mb-1 inline-flex w-fit items-center gap-1 text-xs text-gray-500 hover:text-gray-300"
              >
                <ChevronLeft className="size-3.5" />
                {back.label}
              </Link>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-semibold tracking-tight text-gray-100">{title}</h2>
              {actions && <div className="flex items-center gap-2">{actions}</div>}
            </div>
            {subtitle && <div className="text-sm text-gray-500">{subtitle}</div>}
          </div>
          {children}
        </div>
      </main>
    </div>
  )
}

export const card = 'rounded-xl border border-white/10 bg-white/[0.02] p-4'
export const button =
  'inline-flex items-center gap-1.5 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-gray-200 hover:bg-white/5 disabled:opacity-40'
export const primaryButton =
  'inline-flex items-center gap-1.5 rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-900 hover:bg-white disabled:opacity-40'
export const dangerButton =
  'inline-flex items-center gap-1.5 rounded-lg border border-red-400/30 px-3 py-1.5 text-xs text-red-300 hover:bg-red-400/10 disabled:opacity-40'
