import { describe, expect, it } from 'vitest'
import { panelShowsCard } from './presentation'

describe('the result card in the panel', () => {
  it('shows a presented card', () => {
    expect(panelShowsCard('card', true)).toBe(true)
    expect(panelShowsCard('card', false)).toBe(true)
  })
  it('leaves the expanded mode to the viewer window on the desktop', () => {
    expect(panelShowsCard('ampliado', true)).toBe(false)
  })
  it('shows the card for the expanded mode in a browser, which has no viewer window', () => {
    expect(panelShowsCard('ampliado', false)).toBe(true)
  })
  it('shows nothing when nothing is presented', () => {
    expect(panelShowsCard(null, true)).toBe(false)
  })
})
