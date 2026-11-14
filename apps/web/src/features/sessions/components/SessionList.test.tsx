// @vitest-environment jsdom
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { sessionView } from '../../../lib/sessionView'
import { SessionList } from './SessionList'

const sessions = [
  sessionView('Site Sales', { status: 'busy', project: 'Site Sales' }),
  sessionView('Developer', { project: 'Vrummy', waiting: true }),
  sessionView('sistema'),
]

const setup = (selected: string | null = null) => {
  const onSelect = vi.fn()
  render(
    <SessionList sessions={sessions} selected={selected} onSelect={onSelect} onNew={vi.fn()} />,
  )
  return { onSelect, user: userEvent.setup() }
}

describe('SessionList', () => {
  it('shows each session with its project and what it is doing', () => {
    setup()
    const row = screen.getByRole('button', { name: /Developer/ })
    expect(within(row).getByText('Vrummy')).toBeInTheDocument()
    expect(within(row).getByText('Na fila')).toBeInTheDocument()
    expect(
      within(screen.getByRole('button', { name: /sistema/ })).getByText('Geral'),
    ).toBeInTheDocument()
  })

  it('opens a session on click and marks the open one', async () => {
    const { onSelect, user } = setup('Developer')
    expect(screen.getByRole('button', { name: /Developer/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await user.click(screen.getByRole('button', { name: /Site Sales/ }))
    expect(onSelect).toHaveBeenCalledWith('Site Sales')
  })

  it('filters by name or project', async () => {
    const { user } = setup()
    await user.type(screen.getByRole('searchbox', { name: 'Buscar sessão' }), 'vrum')
    expect(screen.getByRole('button', { name: /Developer/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Site Sales/ })).not.toBeInTheDocument()
  })
})
