import type { SessionView } from '../../../api/events'

// Agents stay neutral so Alfred's orb is the only color on screen; red is kept for errors.

type Look = { label: string; dot: string; name: string; pill: string }

export const STATUS: Record<SessionView['status'], Look> = {
  busy: {
    label: 'ocupado',
    dot: 'size-2.5 bg-gray-100',
    name: 'text-gray-100',
    pill: 'border-white/20 bg-white/10 text-gray-100',
  },
  idle: {
    label: 'livre',
    dot: 'size-2 bg-gray-500',
    name: 'text-gray-300',
    pill: 'border-white/10 text-gray-400',
  },
  error: {
    label: 'erro',
    dot: 'size-2 bg-red-400',
    name: 'text-red-200',
    pill: 'border-red-300/30 bg-red-300/10 text-red-200',
  },
}
