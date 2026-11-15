import type { VoiceState } from '../../../api/events'

/** Bars in the floating voice pill; the server sends the same number of bands. */
export const BAR_COUNT = 9

/**
 * Lays the bands out from the middle: the lowest (loudest in speech) in the centre bar,
 * the next ones alternating right and left, so the bars swell out like a voice.
 */
export function arrangeBands(bands: number[], count = BAR_COUNT): number[] {
  const bars = new Array<number>(count).fill(0)
  const middle = Math.floor(count / 2)
  for (let i = 0; i < Math.min(bands.length, count); i++) {
    const step = Math.ceil(i / 2)
    bars[i % 2 ? middle + step : middle - step] = bands[i]
  }
  return bars
}

/**
 * Stand-in bands from the overall loudness, for servers that send no `bands`:
 * each band breathes at its own pace so the bars still move with the voice.
 */
export function bandsFromLevel(level: number, seconds: number, count = BAR_COUNT): number[] {
  return Array.from({ length: count }, (_, i) => {
    const wobble = 0.6 + 0.4 * Math.sin(seconds * (7 + i) + i * 1.7)
    return Math.min(1, Math.max(0, level * wobble * (1 - i * 0.05)))
  })
}

/** Bar height in percent: never below a pill-shaped dot, never past the box. */
export const barHeight = (value: number): number => Math.min(100, Math.max(22, value * 100 + 5))

/** Which bars light up on each beat when there is no live audio (as the ElevenLabs visualizer). */
export function barSequence(state: VoiceState, count = BAR_COUNT): number[][] {
  const all = Array.from({ length: count }, (_, i) => i)
  if (state === 'thinking' || state === 'transcribing') return all.map((x) => [x, count - 1 - x])
  if (state === 'listening') return [[Math.floor(count / 2)], []]
  return [all]
}
