// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { createRef } from 'react'
import { describe, expect, it } from 'vitest'
import type { Level } from '../hooks/useVoice'
import { VoicePill } from './VoicePill'

describe('VoicePill', () => {
  it('stays where the preset puts it: no grab cursor, nothing to drag', () => {
    const level = createRef<Level>() as React.RefObject<Level>
    render(<VoicePill state="listening" level={level} leaving={false} />)
    const pill = screen.getByRole('img', { name: 'Alfred ouvindo' })
    expect(pill.className).not.toMatch(/cursor-grab/)
  })
})
