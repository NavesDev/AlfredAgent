import { describe, expect, it } from 'vitest'
import type { Project } from '../../../api/events'
import { applyProjectEvent, plural } from './projects'

const project = (id: number, name: string): Project => ({
  id,
  name,
  aliases: [],
  description: '',
  workspaces: [],
})

describe('applyProjectEvent', () => {
  it('adds, replaces and removes projects', () => {
    let list = applyProjectEvent([], {
      type: 'project_created',
      project: project(1, 'Recurve'),
      ts: 1,
    })
    list = applyProjectEvent(list, { type: 'project_created', project: project(2, 'Loja'), ts: 1 })
    list = applyProjectEvent(list, {
      type: 'project_updated',
      project: project(1, 'Recurve 2'),
      ts: 1,
    })
    list = applyProjectEvent(list, { type: 'project_deleted', id: 2, ts: 1 })

    expect(list).toEqual([project(1, 'Recurve 2')])
  })

  it('leaves other events alone', () => {
    const list = [project(1, 'Recurve')]

    expect(applyProjectEvent(list, { type: 'session_deleted', name: 'x', ts: 1 })).toBe(list)
  })
})

describe('plural', () => {
  it('counts in Portuguese', () => {
    expect(plural(1, 'ambiente', 'ambientes')).toBe('1 ambiente')
    expect(plural(0, 'sessão', 'sessões')).toBe('0 sessões')
    expect(plural(3, 'sessão', 'sessões')).toBe('3 sessões')
  })
})
