// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { resultView } from '../lib/fixtures'
import { ResultViewer } from './ResultViewer'

const files = ['a.png', 'b.png', 'c.png'].map((name) => ({
  name,
  kind: 'image' as const,
  size: 1,
  exists: true,
}))

const setup = (index = 0) => {
  const actions = { onIndex: vi.fn(), onClose: vi.fn(), onOpen: vi.fn() }
  render(<ResultViewer result={resultView({ files })} index={index} local {...actions} />)
  return actions
}

describe('ResultViewer', () => {
  it('shows the file big with its session and the open buttons', () => {
    const { onOpen } = setup(1)
    expect(screen.getByRole('img', { name: 'b.png' })).toHaveClass('object-contain')
    expect(screen.getByText(/Design ·/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Abrir no app' }))
    fireEvent.click(screen.getByRole('button', { name: 'Pasta' }))
    expect(onOpen.mock.calls).toEqual([
      [1, false],
      [1, true],
    ])
  })

  it('moves with the arrows, the keys and the strip', () => {
    const { onIndex } = setup(1)
    fireEvent.click(screen.getByRole('button', { name: 'Próximo' }))
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    fireEvent.click(screen.getByRole('button', { name: 'c.png' }))
    expect(onIndex.mock.calls).toEqual([[2], [0], [2]])
  })

  it('closes with Esc and the X', () => {
    const { onClose } = setup()
    fireEvent.keyDown(window, { key: 'Escape' })
    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})
