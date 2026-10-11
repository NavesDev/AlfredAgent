import { describe, expect, it } from 'vitest'
import type { AlfredEvent } from '../../../api/events'
import { initialTranscript, reduceTranscript, toMarkdown } from './turns'

const run = (events: AlfredEvent[]) => events.reduce(reduceTranscript, initialTranscript)

describe('reduceTranscript', () => {
  it('builds one turn with timings from a voice exchange', () => {
    const { turns } = run([
      { type: 'voice_state', state: 'listening', ts: 10 },
      { type: 'voice_state', state: 'transcribing', ts: 13 },
      { type: 'transcript', text: 'que horas são', source: 'voice', ts: 13.5 },
      { type: 'voice_state', state: 'thinking', ts: 13.5 },
      { type: 'agent_progress', session: 'alfred', kind: 'tool', content: 'WebSearch', ts: 14 },
      { type: 'voice_state', state: 'speaking', ts: 15 },
      {
        type: 'alfred_reply',
        session: 'alfred',
        text: 'RESUMO: São 10h.',
        summary: 'São 10h.',
        ts: 16,
      },
      { type: 'voice_state', state: 'speaking', ts: 16.2 },
    ])
    expect(turns).toHaveLength(1)
    expect(turns[0]).toMatchObject({
      session: 'alfred',
      userText: 'que horas são',
      sttS: 0.5,
      firstSpeechS: 1.5,
      replyS: 2.5,
      summary: 'São 10h.',
      steps: [{ kind: 'tool', content: 'WebSearch' }],
    })
  })

  it('attaches an error to the open turn and starts fresh afterwards', () => {
    const { turns } = run([
      { type: 'transcript', text: 'oi', source: 'voice', ts: 1 },
      { type: 'error', where: 'alfred', message: 'timeout', ts: 2 },
      { type: 'agent_progress', session: 'alfred', kind: 'text', content: 'late', ts: 3 },
    ])
    expect(turns).toHaveLength(1)
    expect(turns[0].error).toBe('alfred: timeout')
    expect(turns[0].steps).toEqual([])
  })

  it('keeps a reply without a transcript as its own turn', () => {
    const { turns } = run([
      { type: 'alfred_reply', session: 'alfred', text: 'x', summary: '', ts: 5 },
    ])
    expect(turns[0]).toMatchObject({ userText: null, reply: 'x', summary: null })
  })

  it('keeps a delegated session reply as its own turn even mid-turn', () => {
    const { turns } = run([
      { type: 'transcript', text: 'gira a tela', source: 'voice', ts: 1 },
      { type: 'agent_progress', session: 'sistema', kind: 'tool', content: 'Bash', ts: 2 },
      {
        type: 'alfred_reply',
        session: 'sistema',
        text: 'RESUMO: Feito.',
        summary: 'Feito.',
        ts: 3,
      },
    ])
    expect(turns).toHaveLength(2)
    expect(turns[0]).toMatchObject({ reply: null, steps: [] })
    expect(turns[1]).toMatchObject({ session: 'sistema', summary: 'Feito.', userText: null })
  })
})

describe('toMarkdown', () => {
  it('includes speech, reply and timings', () => {
    const { turns } = run([
      { type: 'transcript', text: 'oi', source: 'voice', ts: 1 },
      { type: 'alfred_reply', session: 'alfred', text: 'RESUMO: Olá.', summary: 'Olá.', ts: 2 },
    ])
    const md = toMarkdown(turns)
    expect(md).toContain('**Você (voice):** oi')
    expect(md).toContain('**Alfred (falado):** Olá.')
    expect(md).toContain('resposta 1.00s')
  })
})
