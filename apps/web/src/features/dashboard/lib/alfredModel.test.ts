import { describe, expect, it } from 'vitest'
import { familyOf, withAlfredModel } from './alfredModel'

describe('familyOf', () => {
  it('reads the family from an alias or a full model id', () => {
    expect(familyOf('sonnet')).toBe('sonnet')
    expect(familyOf('claude-opus-5-5')).toBe('opus')
    expect(familyOf('Haiku')).toBe('haiku')
    expect(familyOf('claude-fable-5-2')).toBeNull()
  })
})

describe('withAlfredModel', () => {
  it('changes only the alfred agent and keeps its effort', () => {
    const agents = [
      { kind: 'alfred', model: 'sonnet', effort: 'low' },
      { kind: 'geral', model: 'sonnet', effort: null },
    ]
    expect(withAlfredModel(agents, 'opus')).toEqual([
      { kind: 'alfred', model: 'opus', effort: 'low' },
      { kind: 'geral', model: 'sonnet', effort: null },
    ])
  })
})
