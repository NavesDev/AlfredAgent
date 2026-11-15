// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { SessionView } from '../../../api/events'
import { sessionView } from '../../../lib/sessionView'
import { SessionCard } from './SessionCard'

const dev = sessionView('Developer', {
  kind: 'implementacao',
  label: 'Implementação',
  project: 'Vrummy',
  workspace: 'principal',
  branch: 'feat/checkout',
  status: 'busy',
  task: 'Rodar os testes de checkout',
  context_tokens: 142_000,
  context_max: 200_000,
})

const setup = (session: SessionView = dev) => {
  const actions = { onClose: vi.fn(), onClear: vi.fn(), onDelete: vi.fn(), onChange: vi.fn() }
  render(<SessionCard session={session} {...actions} />)
  return { ...actions, user: userEvent.setup() }
}

describe('SessionCard', () => {
  it('tells where the session works and what it is doing', () => {
    setup()
    expect(screen.getByRole('heading', { name: 'Developer' })).toBeInTheDocument()
    expect(screen.getByText('Vrummy · principal · feat/checkout')).toBeInTheDocument()
    expect(screen.getByText('Trabalhando')).toBeInTheDocument()
    expect(screen.getByText('Rodar os testes de checkout')).toBeInTheDocument()
    expect(screen.getByText('142k / 200k')).toBeInTheDocument()
  })

  it('shows the generated portrait in place of the monogram', () => {
    setup({ ...dev, portrait: '/api/sessions/Developer/portrait?v=1' })
    expect(screen.getByRole('img', { name: 'Retrato de Developer' })).toHaveAttribute(
      'src',
      '/api/sessions/Developer/portrait?v=1',
    )
  })

  it('clears right away but asks before deleting', async () => {
    const { onClear, onDelete, user } = setup()
    await user.click(screen.getByRole('button', { name: 'Limpar conversa' }))
    expect(onClear).toHaveBeenCalledOnce()

    await user.click(screen.getByRole('button', { name: 'Apagar sessão' }))
    expect(onDelete).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Confirmar apagar' }))
    expect(onDelete).toHaveBeenCalledOnce()
  })

  it('cannot delete a protected session', () => {
    setup(sessionView('sistema', { protected: true }))
    expect(screen.queryByRole('button', { name: 'Apagar sessão' })).not.toBeInTheDocument()
  })

  it('explains why the last task failed', () => {
    setup(sessionView('Dev', { status: 'error', last_error: 'Limite de uso atingido' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Limite de uso atingido')
  })

  it('edits the short description Alfred reads', async () => {
    const { onChange, user } = setup({ ...dev, description: 'Cuida do checkout' })
    expect(screen.getByText('Cuida do checkout')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Editar descrição da sessão Developer' }))
    const input = screen.getByRole('textbox', { name: /descrição da sessão Developer/ })
    await user.clear(input)
    await user.type(input, 'Checkout e pagamentos{Enter}')

    expect(onChange).toHaveBeenCalledWith({ description: 'Checkout e pagamentos' })
  })

  it('closes', async () => {
    const { onClose, user } = setup()
    await user.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
