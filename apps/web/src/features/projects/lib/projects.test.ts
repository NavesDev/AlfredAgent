import { describe, expect, it } from 'vitest'
import type { Project, Workspace } from '../../../api/events'
import { applyProjectEvent, byParent, modeOptions, plural } from './projects'

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

describe('byParent', () => {
  const ws = (id: number, parent_id: number | null = null): Workspace => ({
    id,
    project_id: 1,
    name: `w${id}`,
    path: `/w${id}`,
    kind: parent_id ? 'worktree' : 'folder',
    parent_id,
    branch: null,
    description: '',
    implementation_mode: null,
  })

  it('puts each worktree right under the workspace it came from', () => {
    const list = [ws(1), ws(2), ws(3, 1), ws(4, 1), ws(5, 2), ws(6, 3), ws(7, 99)]

    expect(byParent(list).map((w) => [w.id, w.depth])).toEqual([
      [1, 0],
      [3, 1],
      [6, 2],
      [4, 1],
      [2, 0],
      [5, 1],
      [7, 0], // parent missing: stays, at the top level
    ])
  })
})

describe('modeOptions', () => {
  it('names the global default in the follow-the-global option', () => {
    expect(modeOptions('worktree').map((o) => [o.id, o.label])).toEqual([
      ['', 'Global (worktree novo)'],
      ['worktree', 'Worktree novo'],
      ['ambiente', 'No próprio ambiente'],
    ])
  })
})
