// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Orb } from './Orb'

const level = { current: { value: 0, bands: [], at: 0 } }

describe('Orb', () => {
  it('falls back to the CSS orb when WebGL2 is missing', () => {
    render(<Orb state="idle" level={level} webgl={false} />)
    expect(screen.getByRole('img', { name: 'Alfred em espera' })).toHaveAttribute(
      'data-renderer',
      'css',
    )
  })

  it('names the voice state for screen readers', () => {
    render(<Orb state="speaking" level={level} webgl={false} />)
    expect(screen.getByRole('img', { name: 'Alfred falando' })).toBeInTheDocument()
  })
})
