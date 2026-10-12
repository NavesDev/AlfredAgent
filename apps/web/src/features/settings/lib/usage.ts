import type { RateLimit } from '../../../api/events'

// The Claude plan's usage windows as the panel shows them. Times from the server are unix
// seconds; `now` is milliseconds (Date.now()).

const WINDOWS: Record<string, { label: string; short: string }> = {
  five_hour: { label: 'Janela de 5 horas', short: '5h' },
  seven_day: { label: 'Semana', short: 'semana' },
  seven_day_opus: { label: 'Semana · Opus', short: 'Opus' },
  seven_day_sonnet: { label: 'Semana · Sonnet', short: 'Sonnet' },
  overage: { label: 'Uso extra', short: 'extra' },
  unknown: { label: 'Limite do plano', short: 'limite' },
}
const ORDER = Object.keys(WINDOWS)

export const windowLabel = (w: string) => WINDOWS[w]?.label ?? w
export const windowShort = (w: string) => WINDOWS[w]?.short ?? w

export type Tone = 'ok' | 'warn' | 'bad'

/** Gray while there is room, amber when close (or the CLI warns), red once blocked. */
export function toneOf(limit: RateLimit): Tone {
  if (limit.status === 'rejected') return 'bad'
  if (limit.status === 'allowed_warning' || (limit.utilization ?? 0) >= 0.8) return 'warn'
  return 'ok'
}

/** Text color per tone, for the numbers next to a meter. */
export const TONE_TEXT: Record<Tone, string> = {
  ok: 'text-gray-300',
  warn: 'text-amber-200',
  bad: 'text-red-300',
}

export const percentOf = (limit: RateLimit) =>
  limit.utilization == null ? null : Math.round(limit.utilization * 100)

export const sortLimits = (limits: RateLimit[]) =>
  [...limits].sort((a, b) => ORDER.indexOf(a.window) - ORDER.indexOf(b.window))

/** The one the header shows: a blocked window first, then the fullest, then the 5-hour one. */
export function headline(limits: RateLimit[]): RateLimit | null {
  const blocked = limits.find((l) => l.status === 'rejected')
  if (blocked) return blocked
  const known = limits.filter((l) => l.utilization != null)
  if (known.length) return known.reduce((a, b) => (b.utilization! > a.utilization! ? b : a))
  return limits.find((l) => l.window === 'five_hour') ?? limits[0] ?? null
}

const span = (seconds: number) => {
  const minutes = Math.max(1, Math.round(seconds / 60))
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest && hours < 10 ? `${hours} h ${rest} min` : `${hours} h`
}

/** "reinicia em 2 h 10 min", or the day and hour when it is more than a day away. */
export function resetsIn(resetsAt: number | null, now: number): string | null {
  if (resetsAt == null) return null
  const seconds = resetsAt - now / 1000
  if (seconds <= 0) return 'já reiniciou'
  if (seconds < 24 * 3600) return `reinicia em ${span(seconds)}`
  const when = new Date(resetsAt * 1000).toLocaleString('pt-BR', {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
  return `reinicia ${when}`
}

/** How old the reading is: the CLI only reports while a task runs. */
export function readAgo(readAt: number, now: number): string {
  const seconds = now / 1000 - readAt
  return seconds < 60 ? 'lido agora' : `lido há ${span(seconds)}`
}
