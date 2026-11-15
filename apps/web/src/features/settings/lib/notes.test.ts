import { describe, expect, it } from 'vitest'
import { noteBlocks } from './notes'

describe('noteBlocks', () => {
  it('turns CHANGELOG markdown into headings, items and paragraphs', () => {
    const notes = [
      'First release.',
      '',
      '### Features',
      '',
      '* **desktop:** floating pill ([abc123](https://x))',
      '- plain `code` item',
    ].join('\n')

    expect(noteBlocks(notes)).toEqual([
      { kind: 'text', text: 'First release.' },
      { kind: 'heading', text: 'Features' },
      { kind: 'item', text: 'desktop: floating pill' },
      { kind: 'item', text: 'plain code item' },
    ])
  })

  it('is empty for empty notes', () => {
    expect(noteBlocks('  ')).toEqual([])
  })
})
