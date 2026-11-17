// @vitest-environment jsdom
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { resultView } from '../lib/fixtures'
import { ResultCard } from './ResultCard'

const setup = (props: Partial<Parameters<typeof ResultCard>[0]> = {}) => {
  const actions = { onExpand: vi.fn(), onClose: vi.fn(), onOpen: vi.fn() }
  render(<ResultCard result={resultView()} local {...actions} {...props} />)
  return actions
}

afterEach(() => vi.useRealTimers())

describe('ResultCard', () => {
  it('shows an image with its name, folder and expand', () => {
    const { onExpand, onOpen } = setup()
    expect(screen.getByText('Design fez o retrato')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'retrato.png' })).toHaveAttribute(
      'src',
      '/api/results/7/files/0',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Ampliar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Pasta' }))
    expect(onExpand).toHaveBeenCalledWith(0)
    expect(onOpen).toHaveBeenCalledWith(0, true)
  })

  it('pages through several files', () => {
    const files = ['a.png', 'b.png', 'c.png'].map((name) => ({
      name,
      kind: 'image' as const,
      size: 1,
      exists: true,
    }))
    setup({ result: resultView({ files }) })
    expect(screen.getByText('1 de 3')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Próximo' }))
    expect(screen.getByText('2 de 3')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'b.png' })).toBeInTheDocument()
  })

  it('reports up to three changed files and the rest as +N', () => {
    const changes = ['a.py', 'b.py', 'c.py', 'd.py'].map((path) => ({
      path,
      added: 4,
      removed: 1,
    }))
    setup({ result: resultView({ report: 'Mudei o login.', changes, files: [] }) })
    expect(screen.getByText('Retrato pronto, estilo 3D.')).toBeInTheDocument()
    expect(screen.getByText('c.py')).toBeInTheDocument()
    expect(screen.queryByText('d.py')).not.toBeInTheDocument()
    expect(screen.getByText('+1 arquivo')).toBeInTheDocument()
  })

  it('tells a deleted file and offers nothing to open', () => {
    setup({
      result: resultView({ files: [{ name: 'x.webm', kind: 'video', size: 0, exists: false }] }),
    })
    expect(screen.getByText('Arquivo não existe mais')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ampliar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Pasta' })).not.toBeInTheDocument()
  })

  it('opens what it cannot preview', () => {
    const { onOpen } = setup({
      result: resultView({
        files: [{ name: 'build.zip', kind: 'other', size: 4_200_000, exists: true }],
      }),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Abrir no app' }))
    expect(onOpen).toHaveBeenCalledWith(0, false)
    expect(screen.queryByRole('button', { name: 'Ampliar' })).not.toBeInTheDocument()
  })

  it('shows only text on another device', () => {
    setup({ local: false })
    expect(screen.getByText('Arquivos só no computador')).toBeInTheDocument()
    expect(screen.getByText('Retrato pronto, estilo 3D.')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: 'retrato.png' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ampliar' })).not.toBeInTheDocument()
  })

  it('closes on the X', () => {
    const { onClose } = setup()
    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('leaves on its own after a while, unless the mouse is on it', () => {
    vi.useFakeTimers()
    const onDismiss = vi.fn()
    setup({ autoCloseMs: 30_000, onDismiss })
    const card = screen.getByRole('region', { name: 'Design fez o retrato' })

    fireEvent.mouseEnter(card)
    act(() => void vi.advanceTimersByTime(40_000))
    expect(onDismiss).not.toHaveBeenCalled()

    fireEvent.mouseLeave(card)
    act(() => void vi.advanceTimersByTime(30_000))
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('still leaves when the parent re-renders with a new onDismiss', () => {
    vi.useFakeTimers()
    const onDismiss = vi.fn()
    const props = { result: resultView(), local: true, onExpand: vi.fn(), onOpen: vi.fn() }
    const { rerender } = render(
      <ResultCard
        {...props}
        onClose={vi.fn()}
        autoCloseMs={30_000}
        onDismiss={() => onDismiss()}
      />,
    )
    for (let i = 0; i < 40; i++) {
      act(() => void vi.advanceTimersByTime(1_000))
      rerender(
        <ResultCard
          {...props}
          onClose={vi.fn()}
          autoCloseMs={30_000}
          onDismiss={() => onDismiss()}
        />,
      )
    }
    expect(onDismiss).toHaveBeenCalledOnce()
  })
})
