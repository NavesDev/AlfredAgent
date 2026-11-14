import type { CSSProperties, JSX } from 'react'

export type StrandsProps = {
  colors?: string[]
  count?: number
  speed?: number
  amplitude?: number
  waviness?: number
  thickness?: number
  glow?: number
  taper?: number
  spread?: number
  hueShift?: number
  intensity?: number
  saturation?: number
  opacity?: number
  scale?: number
  glass?: boolean
  refraction?: number
  dispersion?: number
  glassSize?: number
  rim?: number
  energy?: number
  /** Synthesizes speech motion when no level is given. */
  listening?: boolean
  /** Audio level 0..1; undefined lets `listening` drive the motion. */
  level?: number
  interactive?: boolean
  clickPulse?: boolean
  intro?: boolean
  lightMode?: boolean
  maxDevicePixelRatio?: number
  className?: string
  style?: CSSProperties
}

export default function Strands(props: StrandsProps): JSX.Element
