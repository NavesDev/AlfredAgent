import { describe, expect, it } from 'vitest'
import { arrangeBands, bandsFromLevel, barHeight, barSequence } from './bars'

describe('arrangeBands', () => {
  it('puts the lowest band in the middle and spreads the rest outwards', () => {
    expect(arrangeBands([9, 8, 7, 6, 5, 4, 3, 2, 1])).toEqual([1, 3, 5, 7, 9, 8, 6, 4, 2])
  })

  it('leaves missing bands at zero', () => {
    expect(arrangeBands([1], 5)).toEqual([0, 0, 1, 0, 0])
  })
})

describe('barHeight', () => {
  it('keeps a minimum dot and caps at the box', () => {
    expect(barHeight(0)).toBe(22)
    expect(barHeight(2)).toBe(100)
  })
})

describe('barSequence', () => {
  it('sweeps from both edges while thinking', () => {
    expect(barSequence('thinking', 3)).toEqual([
      [0, 2],
      [1, 1],
      [2, 0],
    ])
  })

  it('blinks the middle bar while listening without audio', () => {
    expect(barSequence('listening', 5)).toEqual([[2], []])
  })
})

describe('bandsFromLevel', () => {
  it('stays flat in silence', () => {
    expect(bandsFromLevel(0, 1.3)).toEqual(new Array(9).fill(0))
  })

  it('moves with the loudness, within the unit range', () => {
    const quiet = bandsFromLevel(0.1, 2)
    const loud = bandsFromLevel(0.9, 2)
    expect(loud.every((v, i) => v >= quiet[i] && v <= 1)).toBe(true)
    expect(new Set(loud).size).toBeGreaterThan(1)
  })
})
