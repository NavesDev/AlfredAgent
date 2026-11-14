import type { SessionView } from '../api/events'

export type Tone = 'work' | 'queue' | 'idle' | 'sleep' | 'error'
export type Presence = { label: string; tone: Tone }

/** What a session is doing, in one word, for its row and its card. */
export function presence(session: SessionView): Presence {
  if (session.status === 'error') return { label: 'Erro', tone: 'error' }
  if (session.status === 'busy') return { label: 'Trabalhando', tone: 'work' }
  if (session.waiting) return { label: 'Na fila', tone: 'queue' }
  if (session.connected) return { label: 'Livre', tone: 'idle' }
  return { label: 'Dormindo', tone: 'sleep' }
}

/** First letter of up to two words, like a contact without a photo. */
export function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')
}

const GRADIENTS: [string, string][] = [
  ['#64d2ff', '#0a84ff'],
  ['#ffd60a', '#ff9f0a'],
  ['#da8fff', '#bf5af2'],
  ['#66d4a0', '#30d158'],
  ['#ff8a80', '#ff375f'],
  ['#7d7aff', '#5e5ce6'],
  ['#aeaeb2', '#636366'],
]

/** A stable gradient per name, so a session keeps its colour across reloads. */
export function gradientFor(name: string): [string, string] {
  let hash = 0
  for (const char of name.toLowerCase()) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return GRADIENTS[hash % GRADIENTS.length]
}

export type ContextLevel = { share: number; tone: 'ok' | 'warm' | 'hot' }

/** How full the context window is; near the top the session compacts or fails. */
export function contextLevel(used: number | null, max: number | null): ContextLevel | null {
  if (used == null || !max) return null
  const share = Math.min(100, Math.round((used / max) * 100))
  return { share, tone: share >= 80 ? 'hot' : share >= 60 ? 'warm' : 'ok' }
}
