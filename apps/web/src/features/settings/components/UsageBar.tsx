import type { Tone } from '../lib/usage'

const FILL: Record<Tone, string> = { ok: 'bg-ink-2', warn: 'bg-apple-orange', bad: 'bg-apple-red' }

/** A thin meter; an unknown share draws an empty track. */
export function UsageBar({
  percent,
  tone,
  className = 'h-1.5 w-full',
}: {
  percent: number | null
  tone: Tone
  className?: string
}) {
  return (
    <span className={`block overflow-hidden rounded-full bg-fill ${className}`}>
      <span
        className={`block h-full rounded-full transition-[width] duration-700 ${FILL[tone]}`}
        style={{ width: `${percent ?? 0}%` }}
      />
    </span>
  )
}
