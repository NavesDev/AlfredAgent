import { describe, expect, it } from 'vitest'
import { hasWebGL2, orbMotion } from './orb'

describe('orbMotion', () => {
  it('rests while idle', () => {
    expect(orbMotion('idle', null)).toEqual({ listening: false, level: 0, speed: 0.5, energy: 0.4 })
  })

  it('follows the live audio level while listening or speaking', () => {
    expect(orbMotion('listening', 0.7)).toMatchObject({ listening: true, level: 0.7 })
    expect(orbMotion('speaking', 0.2)).toMatchObject({ listening: true, level: 0.2 })
  })

  it('lets the orb synthesize speech when no fresh level arrived', () => {
    expect(orbMotion('listening', null).level).toBeUndefined()
  })

  it('turns faster and calmer while thinking', () => {
    expect(orbMotion('thinking', 0.9)).toEqual({
      listening: false,
      level: 0.3,
      speed: 1.8,
      energy: 0.6,
    })
  })
})

describe('hasWebGL2', () => {
  const canvas = (getContext: () => unknown) => () =>
    ({ getContext }) as unknown as HTMLCanvasElement

  it('is true when a webgl2 context can be created', () => {
    expect(hasWebGL2(canvas(() => ({})))).toBe(true)
  })

  it('is false when the context is missing or creating it throws', () => {
    expect(hasWebGL2(canvas(() => null))).toBe(false)
    expect(
      hasWebGL2(
        canvas(() => {
          throw new Error('blocked')
        }),
      ),
    ).toBe(false)
  })
})
