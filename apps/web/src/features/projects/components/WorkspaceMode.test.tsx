// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WorkspaceMode } from './WorkspaceMode'

const show = (props: Partial<Parameters<typeof WorkspaceMode>[0]> = {}) => {
  const onDefault = vi.fn()
  const onMode = vi.fn()
  render(
    <WorkspaceMode
      name="principal"
      isDefault={false}
      mode={null}
      globalMode="worktree"
      onDefault={onDefault}
      onMode={onMode}
      {...props}
    />,
  )
  return { onDefault, onMode }
}

describe('WorkspaceMode', () => {
  it('marks the default workspace', () => {
    show({ isDefault: true })
    expect(screen.getByText('padrão')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Tornar principal padrão/ })).toBeNull()
  })

  it('makes another workspace the default', () => {
    const { onDefault } = show()
    fireEvent.click(screen.getByRole('button', { name: 'Tornar principal padrão' }))
    expect(onDefault).toHaveBeenCalled()
  })

  it('shows the global mode until the workspace picks its own', () => {
    const { onMode } = show()
    const picker = screen.getByRole('button', { name: /Features em principal/ })
    expect(picker).toHaveTextContent('Global (worktree novo)')

    fireEvent.click(picker)
    fireEvent.click(screen.getByRole('option', { name: /No próprio ambiente/ }))
    expect(onMode).toHaveBeenCalledWith('ambiente')
  })

  it('goes back to the global mode with null', () => {
    const { onMode } = show({ mode: 'ambiente' })
    fireEvent.click(screen.getByRole('button', { name: /Features em principal/ }))
    fireEvent.click(screen.getByRole('option', { name: /Global/ }))
    expect(onMode).toHaveBeenCalledWith(null)
  })
})
