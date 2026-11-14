// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { sessionView } from '../lib/sessionView'
import { SessionPhoto } from './SessionPhoto'

describe('SessionPhoto', () => {
  it('shows the initials while the session has no portrait', () => {
    render(<SessionPhoto session={sessionView('Site Sales')} size={36} />)
    expect(screen.getByText('SS')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('shows the portrait when there is one', () => {
    render(<SessionPhoto session={sessionView('Design')} src="/portraits/design.jpg" size={36} />)
    expect(screen.getByRole('img', { name: 'Retrato de Design' })).toHaveAttribute(
      'src',
      '/portraits/design.jpg',
    )
  })

  it('rings the photo with what the session is doing', () => {
    const { container } = render(
      <SessionPhoto session={sessionView('Dev', { status: 'busy' })} size={36} />,
    )
    expect(container.firstChild).toHaveAttribute('data-tone', 'work')
  })
})
