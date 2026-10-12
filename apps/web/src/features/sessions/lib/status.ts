import type { SessionView } from '../../../api/events'
import type { MiniLook } from '../../../lib/orb/MiniOrb'

type Look = { label: string; color: string; text: string; pill: string; orb: MiniLook }

export const STATUS: Record<SessionView['status'], Look> = {
  busy: {
    label: 'ocupado',
    color: '#fbbf24',
    text: 'text-amber-200',
    pill: 'border-amber-300/30 bg-amber-300/10 text-amber-200',
    orb: { core: '#451a03', rim: '#fbbf24', active: true },
  },
  idle: {
    label: 'livre',
    color: '#34d399',
    text: 'text-emerald-200',
    pill: 'border-emerald-300/30 bg-emerald-300/10 text-emerald-200',
    orb: { core: '#052e2b', rim: '#34d399', active: false },
  },
  error: {
    label: 'erro',
    color: '#f87171',
    text: 'text-red-200',
    pill: 'border-red-300/30 bg-red-300/10 text-red-200',
    orb: { core: '#450a0a', rim: '#f87171', active: false },
  },
}

export const formatTokens = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`)
