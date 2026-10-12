import type { SubagentView } from '../../../api/events'

// Subagents as small squares tied to the session's node, flashing while they work.
const RADIUS = 36
const ANGLES = [-50, 50, -100, 100, -145, 145].map((deg) => (deg * Math.PI) / 180)

export function SubagentDots({ subagents }: { subagents: SubagentView[] }) {
  const visible = subagents.slice(0, ANGLES.length)
  if (!visible.length) return null
  return (
    <div className="pointer-events-none absolute top-1/2 left-1/2">
      <svg className="absolute overflow-visible" aria-hidden="true">
        {visible.map((s, i) => (
          <line
            key={s.id}
            x1={0}
            y1={0}
            x2={Math.sin(ANGLES[i]) * RADIUS}
            y2={-Math.cos(ANGLES[i]) * RADIUS}
            stroke="#3a3a40"
            strokeWidth={1}
            opacity={s.status === 'running' ? 1 : 0.3}
          />
        ))}
      </svg>
      {visible.map((s, i) => (
        <span
          key={s.id}
          title={`${s.type}: ${s.description}${s.last_tool ? ` · ${s.last_tool}` : ''}`}
          style={{
            left: Math.sin(ANGLES[i]) * RADIUS,
            top: -Math.cos(ANGLES[i]) * RADIUS,
          }}
          className={`absolute flex -translate-y-1/2 items-center gap-1 transition-opacity duration-700 ${
            ANGLES[i] < 0 ? '-translate-x-[calc(100%-3px)] flex-row-reverse' : '-translate-x-[3px]'
          } ${s.status === 'running' ? 'opacity-100' : 'opacity-0'}`}
        >
          <i
            className={`block size-1.5 border border-gray-400 bg-[#111113] ${
              s.status === 'running' ? 'animate-subagent' : ''
            }`}
          />
          <span className="font-mono text-[9px] whitespace-nowrap text-gray-500">{s.type}</span>
        </span>
      ))}
    </div>
  )
}
