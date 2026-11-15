import type { Tone } from '../lib/usage'

const STROKE: Record<Tone, string> = { ok: '#64d2ff', warn: '#ff9f0a', bad: '#ff453a' }
const R = 44
const LENGTH = 2 * Math.PI * R

/** The ring itself: a faint track and the used share drawn clockwise from the top. */
export function Arc({
  share,
  color,
  className,
}: {
  share: number
  color: string
  className?: string
}) {
  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden>
      <circle cx="50" cy="50" r={R} fill="none" stroke="rgb(255 255 255 / 0.12)" strokeWidth="9" />
      {share > 0 && (
        <circle
          cx="50"
          cy="50"
          r={R}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${LENGTH * share} ${LENGTH}`}
          transform="rotate(-90 50 50)"
          className="transition-[stroke-dasharray] duration-700"
        />
      )}
    </svg>
  )
}

type Props = { percent: number | null; tone: Tone; label: string; note?: string }

/** One window of the plan as an Apple Watch ring, the share used in the middle. */
export function UsageRing({ percent, tone, label, note }: Props) {
  const share = Math.min(100, Math.max(0, percent ?? 0)) / 100
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent ?? undefined}
      className="grid justify-items-center gap-2 rounded-[20px] bg-well px-2 py-4 text-center"
    >
      <span className="relative grid size-[110px] place-items-center">
        <Arc share={share} color={STROKE[tone]} className="absolute inset-0" />
        <span className="text-xl font-semibold tabular-nums">
          {percent == null ? '—' : `${percent}%`}
        </span>
      </span>
      <span className="text-[13.5px] font-medium">{label}</span>
      {note && <span className="text-[11.5px] text-ink-2">{note}</span>}
    </div>
  )
}
