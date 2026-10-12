import type { ReactNode } from 'react'
import { Nav } from './Nav'

/** Header with the app name and navigation, then a scrolling content column. */
export function PageShell({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <div className="flex h-full flex-col bg-[radial-gradient(ellipse_at_top,#0d1424_0%,#05070d_70%)]">
      <header className="flex items-center justify-between px-5 py-4">
        <h1 className="text-base font-semibold tracking-[0.3em] text-gray-200 uppercase">Alfred</h1>
        <Nav />
      </header>
      <main className="min-h-0 flex-1 overflow-y-auto px-5 pb-10">
        <div className="mx-auto flex max-w-3xl flex-col gap-5">
          <h2 className="text-lg font-medium text-gray-100">{title}</h2>
          {children}
        </div>
      </main>
    </div>
  )
}

export const card = 'rounded-xl border border-white/10 bg-white/[0.02] p-4'
export const button =
  'rounded-md border border-white/15 px-3 py-1.5 text-xs text-gray-200 hover:bg-white/5 disabled:opacity-40'
