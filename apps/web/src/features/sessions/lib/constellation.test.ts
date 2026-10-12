import { describe, expect, it } from 'vitest'
import { sessionView } from '../../../lib/sessionView'
import { filamentPath, layout, nodePositions, pulseFor, type Stage } from './constellation'

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

describe('layout', () => {
  const sessions = [
    sessionView('sistema'),
    sessionView('back', { project: 'Recurve' }),
    sessionView('front', { project: 'Recurve' }),
    sessionView('api', { project: 'Loja' }),
  ]
  const round = (p: { x: number; y: number }) => `${Math.round(p.x)},${Math.round(p.y)}`
  const dist = (p: { x: number; y: number }) => Math.hypot(p.x - stage.cx, p.y - stage.cy)

  it('gives each project one hub between the orb and its sessions', () => {
    const { hubs, nodes } = layout(sessions, stage)

    expect(hubs.map((h) => h.project)).toEqual(['Recurve', 'Loja'])
    const recurve = hubs[0]
    for (const name of ['back', 'front']) {
      const node = nodes.find((n) => n.name === name)!
      expect(dist(recurve.at)).toBeLessThan(dist(node.at))
      expect(dist(recurve.at)).toBeGreaterThan(stage.r)
    }
  })

  it('ties sessions without a project straight to the orb', () => {
    const sistema = layout(sessions, stage).nodes.find((n) => n.name === 'sistema')!

    expect(sistema.branch).toBeNull()
    expect(sistema.d).toBe(filamentPath(stage, sistema.at))
  })

  it('runs a grouped session path through its hub, for the pulses', () => {
    const { hubs, nodes } = layout(sessions, stage)
    const back = nodes.find((n) => n.name === 'back')!
    const hub = hubs[0].at

    expect(back.branch!.startsWith(`M${+hub.x.toFixed(1)} ${+hub.y.toFixed(1)} Q`)).toBe(true)
    expect(back.d.startsWith(hubs[0].d)).toBe(true)
    expect(back.d.endsWith(`${+back.at.x.toFixed(1)} ${+back.at.y.toFixed(1)}`)).toBe(true)
  })

  it('keeps every node distinct and inside the stage', () => {
    const { nodes } = layout(sessions, stage)

    expect(new Set(nodes.map((n) => round(n.at))).size).toBe(4)
    for (const { at } of nodes) {
      expect(at.x).toBeGreaterThanOrEqual(56)
      expect(at.x).toBeLessThanOrEqual(stage.width - 56)
      expect(at.y).toBeGreaterThanOrEqual(40)
      expect(at.y).toBeLessThanOrEqual(stage.height - 40)
    }
  })
})
