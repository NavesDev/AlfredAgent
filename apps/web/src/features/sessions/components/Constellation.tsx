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
import { NewSessionForm } from '../../../components/NewSessionForm'
import { useProjectList } from '../hooks/useProjectList'
import { useSessionActions } from '../hooks/useSessionActions'
import { useTerminal } from '../hooks/useTerminal'
import { layout, pulseFor, type Point, type Stage } from '../lib/constellation'
import { AgentDetails } from './AgentDetails'
import { AgentNode } from './AgentNode'
import { ProjectHub } from './ProjectHub'

// The orb's sphere fills about this share of its canvas' shorter half (camera at z 4.2, fov 45).
const ORB_SHARE = 0.55
const DETAILS_W = 288
const FILAMENT = '#9ca3af' // neutral gray: the line only says who is tied to whom

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

function placement(at: Point, stage: Stage): CSSProperties {
  const left = Math.min(Math.max(at.x - DETAILS_W / 2, 8), stage.width - DETAILS_W - 8)
  return at.y < stage.height / 2
    ? { left, top: at.y + 56 }
    : { left, bottom: stage.height - at.y + 40 }
}

/** Agent sessions around Alfred's orb, grouped under their project's diamond. */
export function Constellation({ anchor }: { anchor: RefObject<HTMLElement | null> }) {
  const sessions = useSessions()
  const projects = useProjectList()
  const terminal = useTerminal()
  const { create } = useSessionActions()
  const box = useRef<HTMLDivElement>(null)
  const stage = useStage(box, anchor)
  const { pulses, done } = usePulses()
  // "s:<name>" opens a session's details, "p:<project>" a hub's menu, "n:<project>" the form
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

  const { hubs, nodes } = stage ? layout(sessions, stage) : { hubs: [], nodes: [] }
  const nodeOf = new Map(nodes.map((n) => [n.name, n]))
  const opened = open?.startsWith('s:') ? sessions.find((s) => s.name === open.slice(2)) : undefined
  const formFor = open?.startsWith('n:') ? hubs.find((h) => h.project === open.slice(2)) : undefined
  const projectId = (name: string) => projects.find((p) => p.name === name)?.id
  const toggle = (key: string) => setOpen((o) => (o === key ? null : key))

  return (
    <div
      ref={box}
      aria-label="Sessões"
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {stage && (
        <svg className="absolute inset-0 z-0 h-full w-full overflow-visible" aria-hidden="true">
          {hubs.map((hub) => {
            const busy = sessions.some((s) => s.project === hub.project && s.status === 'busy')
            return <Filament key={`hub-${hub.project}`} d={hub.d} busy={busy} />
          })}
          {sessions.map((s) => {
            const node = nodeOf.get(s.name)
            if (!node) return null
            return <Filament key={s.name} d={node.branch ?? node.d} busy={s.status === 'busy'} />
          })}
        </svg>
      )}
      {stage &&
        pulses.map((pulse) => {
          const node = nodeOf.get(pulse.name)
          if (!node) return null
          return (
            <span
              key={pulse.id}
              onAnimationEnd={() => done(pulse.id)}
              style={{
                offsetPath: `path('${node.d}')`,
                offsetRotate: '0deg',
                background: FILAMENT,
                boxShadow: `0 0 10px 3px ${FILAMENT}`,
              }}
              className={`absolute top-0 left-0 z-0 size-2 rounded-full ${
                pulse.dir === 'out' ? 'animate-pulse-out' : 'animate-pulse-in'
              }`}
            />
          )
        })}
      {hubs.map((hub) => (
        <ProjectHub
          key={hub.project}
          project={hub.project}
          projectId={projectId(hub.project)}
          at={hub.at}
          open={open === `p:${hub.project}`}
          onToggle={() => toggle(`p:${hub.project}`)}
          onNewSession={() => setOpen(`n:${hub.project}`)}
        />
      ))}
      {sessions.map((s) => {
        const node = nodeOf.get(s.name)
        if (!node) return null
        return (
          <AgentNode
            key={s.name}
            session={s}
            at={node.at}
            open={open === `s:${s.name}`}
            lines={terminal[s.name] ?? []}
            onToggle={() => toggle(`s:${s.name}`)}
          />
        )
      })}
      {opened && stage && nodeOf.get(opened.name) && (
        <AgentDetails
          key={opened.name}
          session={opened}
          onClose={() => setOpen(null)}
          style={placement(nodeOf.get(opened.name)!.at, stage)}
        />
      )}
      {formFor && stage && (
        <div
          role="dialog"
          aria-label={`Nova sessão em ${formFor.project}`}
          style={placement(formFor.at, stage)}
          onPointerDown={(e) => e.stopPropagation()}
          className="animate-activity-in pointer-events-auto absolute z-30 w-80 rounded-xl border border-white/10 bg-[#0a0f1c]/95 p-3 backdrop-blur"
        >
          <h3 className="mb-2 text-sm font-medium text-gray-100">
            Nova sessão em {formFor.project}
          </h3>
          <NewSessionForm
            projects={projects}
            projectId={projectId(formFor.project)}
            pending={create.isPending}
            error={create.error?.message}
            onCancel={() => setOpen(null)}
            onSubmit={(body) => create.mutate(body, { onSuccess: () => setOpen(null) })}
          />
        </div>
      )}
    </div>
  )
}

function Filament({ d, busy }: { d: string; busy: boolean }) {
  return (
    <path
      d={d}
      fill="none"
      stroke={FILAMENT}
      strokeWidth={busy ? 1.5 : 1}
      strokeOpacity={busy ? 0.7 : 0.3}
      strokeDasharray={busy ? '4 8' : undefined}
      strokeLinecap="round"
      className={busy ? 'animate-filament' : undefined}
    />
  )
}
