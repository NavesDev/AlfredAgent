import { describe, expect, it } from 'vitest'
import { filamentPath, nodePositions, pulseFor, type Stage } from './constellation'

const stage: Stage = { cx: 400, cy: 300, r: 100, width: 800, height: 600 }

describe('nodePositions', () => {
  it('puts the first two nodes on opposite sides of the orb', () => {
    const [a, b] = nodePositions(2, stage)

    expect(a.x).toBeLessThan(stage.cx - stage.r)
    expect(b.x).toBeGreaterThan(stage.cx + stage.r)
  })

  it('keeps every node outside the orb and inside the stage', () => {
    for (const p of nodePositions(6, stage)) {
      expect(Math.hypot(p.x - stage.cx, p.y - stage.cy)).toBeGreaterThan(stage.r * 1.4)
      expect(p.x).toBeGreaterThanOrEqual(56)
      expect(p.x).toBeLessThanOrEqual(stage.width - 56)
      expect(p.y).toBeGreaterThanOrEqual(40)
      expect(p.y).toBeLessThanOrEqual(stage.height - 40)
    }
  })

  it('gives distinct positions', () => {
    const keys = nodePositions(6, stage).map((p) => `${Math.round(p.x)},${Math.round(p.y)}`)

    expect(new Set(keys).size).toBe(6)
  })
})

describe('filamentPath', () => {
  it('runs from the orb center to the node, both hidden behind their orbs', () => {
    const d = filamentPath(stage, { x: 100, y: 300 })

    expect(d.startsWith('M400 300 Q')).toBe(true)
    expect(d.endsWith('100 300')).toBe(true)
  })
})

describe('pulseFor', () => {
  it('sends a pulse out when a task starts and back when it ends', () => {
    expect(pulseFor('idle', 'busy')).toBe('out')
    expect(pulseFor('busy', 'idle')).toBe('in')
    expect(pulseFor('busy', 'error')).toBe('in')
    expect(pulseFor('idle', 'idle')).toBeNull()
    expect(pulseFor(undefined, 'busy')).toBe('out')
    expect(pulseFor(undefined, 'idle')).toBeNull()
  })
})
