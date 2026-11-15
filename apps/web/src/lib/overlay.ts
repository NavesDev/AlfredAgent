/** Where the desktop overlay is anchored (apps/desktop `overlay_anchor`). */
export type Anchor = { edge: 'top' | 'bottom'; align: 'left' | 'center' | 'right' }

const ALIGN = { left: 'items-start', center: 'items-center', right: 'items-end' } as const

/** Flex-column classes that pin the pill and the card to the anchored corner of the window. */
export const anchorClasses = ({ edge, align }: Anchor) =>
  `${edge === 'top' ? 'justify-start' : 'justify-end'} ${ALIGN[align]}`

/** The rectangle that takes the mouse, in whole logical pixels (outward). */
export function hitRect(box: { left: number; top: number; width: number; height: number }) {
  const x = Math.floor(box.left)
  const y = Math.floor(box.top)
  return [x, y, Math.ceil(box.left + box.width) - x, Math.ceil(box.top + box.height) - y] as [
    number,
    number,
    number,
    number,
  ]
}

/** What the overlay shows: the card (a result presented while the panel is out of sight), the
 * voice pill (Alfred busy, out of sight) or nothing. The expanded mode lives in its own window. */
export function overlayShows({
  active,
  outOfSight,
  presentation,
}: {
  active: boolean
  outOfSight: boolean
  presentation: { mode: 'card' | 'ampliado' } | null
}): 'card' | 'pill' | 'none' {
  if (!outOfSight) return 'none'
  if (presentation?.mode === 'card') return 'card'
  return active ? 'pill' : 'none'
}
