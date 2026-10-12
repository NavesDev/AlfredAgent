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

/** The quadratic segment of a gentle curve from one point to another, without the move. */
function curve(from: Point, to: Point): string {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  const bow = len * 0.18 * (dx < 0 ? 1 : -1)
  const qx = (from.x + to.x) / 2 + (-dy / len) * bow
  const qy = (from.y + to.y) / 2 + (dx / len) * bow
  return `Q${n(qx)} ${n(qy)} ${n(to.x)} ${n(to.y)}`
}

const move = (p: Point) => `M${n(p.x)} ${n(p.y)}`

/** A gentle curve from the orb's center to the node; both ends sit behind their orbs. */
export function filamentPath({ cx, cy }: Stage, to: Point): string {
  return `${move({ x: cx, y: cy })} ${curve({ x: cx, y: cy }, to)}`
}

// Sessions of a project hang from a hub (the project's diamond) between the orb and them.
const HUB_AT = 0.55 // share of the way from the orb to the group's slot
const SPREAD = 0.34 // radians between sessions of the same project

export type Hub = { project: string; at: Point; d: string }
/** d: orb → (hub →) node, for the pulses. branch: hub → node, null without a project. */
export type Node = { name: string; at: Point; d: string; branch: string | null }
export type Layout = { hubs: Hub[]; nodes: Node[] }

export function layout(sessions: SessionView[], stage: Stage): Layout {
  const { cx, cy, width, height } = stage
  const groups: { project: string | null; names: string[] }[] = []
  for (const s of sessions) {
    const group = s.project ? groups.find((g) => g.project === s.project) : undefined
    if (group) group.names.push(s.name)
    else groups.push({ project: s.project ?? null, names: [s.name] })
  }
  const slots = nodePositions(groups.length, stage)
  const hubs: Hub[] = []
  const nodes: Node[] = []
  groups.forEach((group, g) => {
    const slot = slots[g]
    const vx = slot.x - cx
    const vy = slot.y - cy
    const hub = group.project
      ? { project: group.project, at: { x: cx + vx * HUB_AT, y: cy + vy * HUB_AT }, d: '' }
      : null
    if (hub) {
      hub.d = filamentPath(stage, hub.at)
      hubs.push(hub)
    }
    group.names.forEach((name, i) => {
      const a = (i - (group.names.length - 1) / 2) * SPREAD
      const at = {
        x: clamp(cx + vx * Math.cos(a) - vy * Math.sin(a), MARGIN_X, width - MARGIN_X),
        y: clamp(cy + vx * Math.sin(a) + vy * Math.cos(a), MARGIN_Y, height - MARGIN_Y),
      }
      nodes.push(
        hub
          ? {
              name,
              at,
              d: `${hub.d} ${curve(hub.at, at)}`,
              branch: `${move(hub.at)} ${curve(hub.at, at)}`,
            }
          : { name, at, d: filamentPath(stage, at), branch: null },
      )
    })
  })
  return { hubs, nodes }
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
