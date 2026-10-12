import type { SessionView } from '../../../api/events'

// Geometry of the constellation: agents as nodes around Alfred's orb, tied by filaments.

/** Orb center and radius inside a stage of the given size, all in px. */
export type Stage = { cx: number; cy: number; r: number; width: number; height: number }
export type Point = { x: number; y: number }

// Sides first, then above, then below (y grows downward). Below is where the captions live.
const ANGLES = [170, 10, 210, 330, 140, 40].map((deg) => (deg * Math.PI) / 180)
const MARGIN_X = 56 // room for the label under a node
const MARGIN_Y = 40

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
const n = (v: number) => Number(v.toFixed(1))

export function nodePositions(count: number, { cx, cy, r, width, height }: Stage): Point[] {
  const rx = Math.max(r * 2.1, Math.min(width * 0.36, r * 3.2))
  const ry = r * 1.7
  return Array.from({ length: count }, (_, i) => {
    const a = ANGLES[i % ANGLES.length] + Math.floor(i / ANGLES.length) * 0.25
    return {
      x: clamp(cx + Math.cos(a) * rx, MARGIN_X, width - MARGIN_X),
      y: clamp(cy + Math.sin(a) * ry, MARGIN_Y, height - MARGIN_Y),
    }
  })
}

/** A gentle curve from the orb's edge to the node, bowing upward. */
export function filamentPath({ cx, cy, r }: Stage, to: Point): string {
  const dx = to.x - cx
  const dy = to.y - cy
  const len = Math.hypot(dx, dy) || 1
  const sx = cx + (dx / len) * r
  const sy = cy + (dy / len) * r
  const bow = len * 0.18 * (dx < 0 ? 1 : -1)
  const qx = (sx + to.x) / 2 + (-dy / len) * bow
  const qy = (sy + to.y) / 2 + (dx / len) * bow
  return `M${n(sx)} ${n(sy)} Q${n(qx)} ${n(qy)} ${n(to.x)} ${n(to.y)}`
}

/** Light runs Alfred → agent when a task starts and back when it ends. */
export function pulseFor(
  before: SessionView['status'] | undefined,
  after: SessionView['status'],
): 'out' | 'in' | null {
  if (after === 'busy' && before !== 'busy') return 'out'
  if (before === 'busy' && after !== 'busy') return 'in'
  return null
}
