import { Link } from 'react-router'
import { useNow, useUsage } from '../hooks/useUsage'
import {
  TONE_TEXT,
  headline,
  percentOf,
  readAgo,
  toneOf,
  windowLabel,
  windowShort,
} from '../lib/usage'
import { UsageBar } from './UsageBar'

/** The header's short meter: the window closest to its limit; the details are in settings. */
export function UsagePill() {
  const usage = useUsage()
  const now = useNow()
  const limit = usage ? headline(usage.limits) : null
  const base =
    'flex items-center gap-1.5 rounded-full px-3 py-2 text-[11.5px] whitespace-nowrap hover:bg-fill'

  if (!limit) {
    return (
      <Link
        to="/settings#uso"
        title="Os limites aparecem depois que o Alfred ou uma sessão trabalhar"
        className={`${base} text-ink-3`}
      >
        limites —
      </Link>
    )
  }
  const percent = percentOf(limit)
  const tone = toneOf(limit)
  return (
    <Link
      to="/settings#uso"
      title={`${windowLabel(limit.window)}: ${percent ?? '?'}% · ${readAgo(limit.read_at, now)}`}
      className={`${base} ${TONE_TEXT[tone]}`}
    >
      <span>{windowShort(limit.window)}</span>
      <UsageBar percent={percent} tone={tone} className="h-1 w-8" />
      <span className="tabular-nums">
        {limit.status === 'rejected' ? 'bloqueado' : percent == null ? 'ok' : `${percent}%`}
      </span>
    </Link>
  )
}
