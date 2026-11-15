import type { OverlayPosition } from '../../../api/events'
import type { PickerOption } from '../../../components/Picker'

/** Every preset the desktop overlay anchors to (server OverlayPosition), in the order shown. */
export const POSITIONS: (PickerOption & { id: OverlayPosition })[] = [
  { id: 'top_left', label: 'Em cima à esquerda' },
  { id: 'top_center', label: 'Em cima no centro' },
  { id: 'top_right', label: 'Em cima à direita' },
  { id: 'bottom_left', label: 'Embaixo à esquerda' },
  { id: 'bottom_center', label: 'Embaixo no centro' },
  { id: 'bottom_right', label: 'Embaixo à direita' },
]

const SPOT: Record<OverlayPosition, string> = {
  top_left: 'top-1 left-1',
  top_center: 'top-1 left-1/2 -translate-x-1/2',
  top_right: 'top-1 right-1',
  bottom_left: 'bottom-1 left-1',
  bottom_center: 'bottom-1 left-1/2 -translate-x-1/2',
  bottom_right: 'bottom-1 right-1',
}

/** A tiny screen with the pill drawn where the preset puts it. */
export function OverlaySpot({ position }: { position: OverlayPosition }) {
  const label = POSITIONS.find((p) => p.id === position)?.label ?? position
  return (
    <span
      role="img"
      aria-label={label}
      className="relative block h-9 w-14 shrink-0 rounded-md border-[1.5px] border-white/35 bg-black/25"
    >
      <span className={`absolute h-1.5 w-4 rounded-full bg-ink ${SPOT[position]}`} />
    </span>
  )
}
