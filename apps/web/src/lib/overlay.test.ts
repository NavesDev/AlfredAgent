import { describe, expect, it } from 'vitest'
import { anchorClasses, hitRect, overlayShows } from './overlay'

describe('overlay layout', () => {
  it('pins what floats to the preset corner of the window', () => {
    expect(anchorClasses({ edge: 'top', align: 'right' })).toBe('justify-start items-end')
    expect(anchorClasses({ edge: 'bottom', align: 'center' })).toBe('justify-end items-center')
    expect(anchorClasses({ edge: 'top', align: 'left' })).toBe('justify-start items-start')
  })

  it('reports the card box as whole pixels', () => {
    expect(hitRect({ left: 10.4, top: 0, width: 300.2, height: 220.6 })).toEqual([10, 0, 301, 221])
  })
})

describe('what the overlay shows', () => {
  const card = { mode: 'card' as const }
  it('shows nothing while the panel is in sight', () => {
    expect(overlayShows({ active: true, outOfSight: false, presentation: card })).toBe('none')
  })
  it('turns the pill into the card when a result is presented out of sight', () => {
    expect(overlayShows({ active: true, outOfSight: true, presentation: card })).toBe('card')
    expect(overlayShows({ active: false, outOfSight: true, presentation: card })).toBe('card')
  })
  it('keeps the pill while Alfred is busy and nothing is presented', () => {
    expect(overlayShows({ active: true, outOfSight: true, presentation: null })).toBe('pill')
    expect(overlayShows({ active: false, outOfSight: true, presentation: null })).toBe('none')
  })
  it('leaves the expanded mode to the viewer window', () => {
    const expanded = { mode: 'ampliado' as const }
    expect(overlayShows({ active: true, outOfSight: true, presentation: expanded })).toBe('pill')
  })
})
