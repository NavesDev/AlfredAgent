import type { FileChange, ResultFile } from '../../../api/events'

/** Text bigger than this is not previewed (docs/DESIGN.md#results). */
export const TEXT_MAX = 1_000_000
/** Changed files listed on the card before "+N". */
export const CHANGES_SHOWN = 3

export const fileUrl = (id: number, index: number) => `/api/results/${id}/files/${index}`

/** Files reach only this computer (RN-12); the panel decides by the page's own host. */
export const isLocalHost = (hostname: string) =>
  ['localhost', '127.0.0.1', '::1', '[::1]'].includes(hostname)

export function shownChanges(changes: FileChange[]) {
  return {
    shown: changes.slice(0, CHANGES_SHOWN),
    more: Math.max(0, changes.length - CHANGES_SHOWN),
  }
}

export function totals(changes: FileChange[]) {
  return changes.reduce(
    (sum, c) => ({ added: sum.added + c.added, removed: sum.removed + c.removed }),
    { added: 0, removed: 0 },
  )
}

export function formatSize(bytes: number): string {
  if (bytes < 1000) return `${bytes} B`
  if (bytes < 1_000_000) return `${Math.round(bytes / 1000)} KB`
  return `${(bytes / 1_000_000).toFixed(1).replace('.', ',')} MB`
}

/** The card's primary button: preview it bigger, open it in its app, or nothing (gone). */
export function mainAction(file: ResultFile): 'expand' | 'open' | 'none' {
  if (!file.exists) return 'none'
  if (file.kind === 'other' || (file.kind === 'text' && file.size > TEXT_MAX)) return 'open'
  return 'expand'
}

/** "14:32" today, "ontem", else "12/11". */
export function timeLabel(epoch: number, now = new Date()): string {
  const at = new Date(epoch * 1000)
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const days = Math.round((day(now) - day(at)) / 86_400_000)
  if (days === 0) return at.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  if (days === 1) return 'ontem'
  return at.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

/** What a result pages through: its report first (if any), then each file. */
export type Slide = { type: 'report' } | { type: 'file'; index: number; file: ResultFile }

export function slidesOf(result: { report: string | null; files: ResultFile[] }): Slide[] {
  return [
    ...(result.report !== null ? [{ type: 'report' as const }] : []),
    ...result.files.map((file, index) => ({ type: 'file' as const, index, file })),
  ]
}
