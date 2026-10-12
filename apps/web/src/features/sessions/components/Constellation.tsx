import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from 'react'
import type { SessionView } from '../../../api/events'
import { useEvents } from '../../../hooks/useEvents'
import { useSessions } from '../hooks/useSessions'
import { filamentPath, nodePositions, pulseFor, type Point, type Stage } from '../lib/constellation'
import { STATUS } from '../lib/status'
import { AgentDetails } from './AgentDetails'
import { AgentNode } from './AgentNode'

// The orb's sphere fills about this share of its canvas' shorter half (camera at z 4.2, fov 45).
const ORB_SHARE = 0.55
const DETAILS_W = 288

type Pulse = { id: number; name: string; dir: 'out' | 'in' }

/** Measures where Alfred's orb sits inside the overlay, following resizes. */
function useStage(box: RefObject<HTMLElement | null>, anchor: RefObject<HTMLElement | null>) {
  const [stage, setStage] = useState<Stage | null>(null)
  useLayoutEffect(() => {
    const measure = () => {
      if (!box.current || !anchor.current) return
      const b = box.current.getBoundingClientRect()
      const a = anchor.current.getBoundingClientRect()
      setStage({
        cx: a.left - b.left + a.width / 2,
        cy: a.top - b.top + a.height / 2,
        r: (Math.min(a.width, a.height) / 2) * ORB_SHARE,
        width: b.width,
        height: b.height,
      })
    }
    const observer = new ResizeObserver(measure) // also fires once on observe
    for (const el of [box.current, anchor.current]) if (el) observer.observe(el)
    return () => observer.disconnect()
  }, [box, anchor])
  return stage
}

/** Light pulses for tasks starting (Alfred → agent) and ending (agent → Alfred). */
function usePulses() {
  const before = useRef(new Map<string, SessionView['status']>())
  const nextId = useRef(0)
  const [pulses, setPulses] = useState<Pulse[]>([])
  useEvents((event) => {
    if (event.type === 'session_deleted') before.current.delete(event.name)
    if (event.type !== 'session_status' && event.type !== 'session_cleared') return
    const { name, status } = event.session
    const dir = event.type === 'session_status' ? pulseFor(before.current.get(name), status) : null
    before.current.set(name, status)
    if (dir) setPulses((p) => [...p, { id: nextId.current++, name, dir }])
  })
  const done = (id: number) => setPulses((p) => p.filter((x) => x.id !== id))
  return { pulses, done }
}

function detailsPlacement(at: Point, stage: Stage): CSSProperties {
  const left = Math.min(Math.max(at.x - DETAILS_W / 2, 8), stage.width - DETAILS_W - 8)
  return at.y < stage.height / 2
    ? { left, top: at.y + 56 }
    : { left, bottom: stage.height - at.y + 40 }
}

/** Agent sessions as nodes around Alfred's orb, tied to it by filaments. */
export function Constellation({ anchor }: { anchor: RefObject<HTMLElement | null> }) {
  const sessions = useSessions()
  const box = useRef<HTMLDivElement>(null)
  const stage = useStage(box, anchor)
  const { pulses, done } = usePulses()
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(null)
    const onPointer = () => setOpen(null)
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', onPointer)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('pointerdown', onPointer)
    }
  }, [open])

  const points = stage ? nodePositions(sessions.length, stage) : []
  const paths = stage ? points.map((p) => filamentPath(stage, p)) : []
  const index = new Map(sessions.map((s, i) => [s.name, i]))
  const opened = sessions.find((s) => s.name === open)

  return (
    <div ref={box} aria-label="Sessões" className="pointer-events-none absolute inset-0">
      {stage && (
        <svg className="absolute inset-0 h-full w-full overflow-visible" aria-hidden="true">
          {sessions.map((s, i) => {
            const busy = s.status === 'busy'
            return (
              <g key={s.name} stroke={STATUS[s.status].color} fill="none">
                <path d={paths[i]} strokeWidth={6} strokeOpacity={busy ? 0.12 : 0.04} />
                <path
                  d={paths[i]}
                  strokeWidth={busy ? 1.5 : 1}
                  strokeOpacity={busy ? 0.9 : 0.35}
                  strokeDasharray={busy ? '4 8' : undefined}
                  strokeLinecap="round"
                  className={busy ? 'animate-filament' : undefined}
                />
              </g>
            )
          })}
        </svg>
      )}
      {stage &&
        pulses.map((pulse) => {
          const i = index.get(pulse.name)
          if (i === undefined) return null
          const color = STATUS[pulse.dir === 'out' ? 'busy' : 'idle'].color
          return (
            <span
              key={pulse.id}
              onAnimationEnd={() => done(pulse.id)}
              style={{
                offsetPath: `path('${paths[i]}')`,
                offsetRotate: '0deg',
                background: color,
                boxShadow: `0 0 12px 4px ${color}`,
              }}
              className={`absolute top-0 left-0 size-2 rounded-full ${
                pulse.dir === 'out' ? 'animate-pulse-out' : 'animate-pulse-in'
              }`}
            />
          )
        })}
      {sessions.map((s, i) =>
        points[i] ? (
          <AgentNode
            key={s.name}
            session={s}
            at={points[i]}
            open={open === s.name}
            onToggle={() => setOpen((o) => (o === s.name ? null : s.name))}
          />
        ) : null,
      )}
      {opened && stage && points[index.get(opened.name)!] && (
        <AgentDetails
          key={opened.name}
          session={opened}
          onClose={() => setOpen(null)}
          style={detailsPlacement(points[index.get(opened.name)!], stage)}
        />
      )}
    </div>
  )
}
