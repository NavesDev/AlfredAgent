import type { VoiceState } from '../../../api/events'

/** What the Strands orb receives; `level` undefined lets it synthesize speech on its own. */
export type OrbMotion = {
  listening: boolean
  level: number | undefined
  speed: number
  energy: number
}

/** Maps the voice state (and the live audio level, when fresh) to the orb's motion. */
export function orbMotion(state: VoiceState, level: number | null): OrbMotion {
  switch (state) {
    case 'listening':
      return { listening: true, level: level ?? undefined, speed: 1, energy: 0.8 }
    case 'speaking':
      return { listening: true, level: level ?? undefined, speed: 1.1, energy: 0.9 }
    case 'thinking':
    case 'transcribing':
      return { listening: false, level: 0.3, speed: 1.8, energy: 0.6 }
    default:
      return { listening: false, level: 0, speed: 0.5, energy: 0.4 }
  }
}

/** Strands draws nothing without WebGL2 (the desktop app's viewer, some VMs), so check first. */
export function hasWebGL2(
  create: () => HTMLCanvasElement = () => document.createElement('canvas'),
): boolean {
  try {
    return create().getContext('webgl2') != null
  } catch {
    return false
  }
}
