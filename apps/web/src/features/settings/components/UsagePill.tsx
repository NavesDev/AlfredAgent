import { Link } from 'react-router'
import { useNow, useUsage } from '../hooks/useUsage'
import type { Tone } from '../lib/usage'
import { headline, percentOf, readAgo, toneOf, windowLabel, windowShort } from '../lib/usage'
import { Arc } from './UsageRing'

/** White while there is room, like the rest of the control bar; amber and red keep their meaning. */
const COLOR: Record<Tone, string> = { ok: '#f5f5f7', warn: '#ff9f0a', bad: '#ff453a' }

/** The header's short meter: a ring for the window closest to its limit; details in settings. */
export function UsagePill() {
  const usage = useUsage()
  const now = useNow()
  const limit = usage ? headline(usage.limits) : null
  const percent = limit ? percentOf(limit) : null
  const tone = limit ? toneOf(limit) : 'ok'
  const value = !limit
    ? '—'
    : limit.status === 'rejected'
      ? 'bloqueado'
      : percent == null
        ? 'ok'
        : `${percent}%`
  return (
    <Link
      to="/settings#uso"
      title={
        limit
          ? `${windowLabel(limit.window)}: ${percent ?? '?'}% · ${readAgo(limit.read_at, now)}`
          : 'Os limites aparecem depois que o Alfred ou uma sessão trabalhar'
      }
      className="flex items-center gap-2 rounded-full bg-fill py-1.5 pr-3.5 pl-1.5 whitespace-nowrap transition-colors hover:bg-fill-on"
    >
      <Arc share={(percent ?? 0) / 100} color={COLOR[tone]} className="size-[26px] shrink-0" />
      <span className="grid text-left leading-tight">
        <span
          className={`text-[12px] font-medium tabular-nums ${tone === 'ok' ? 'text-ink' : tone === 'warn' ? 'text-apple-orange' : 'text-apple-red'}`}
        >
          {value}
        </span>
        <span className="text-[10.5px] text-ink-2">
          {limit ? windowShort(limit.window) : 'limites'}
        </span>
      </span>
    </Link>
  )
}
