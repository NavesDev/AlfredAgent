// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { resultView } from '../lib/fixtures'
import { ResultList } from './ResultHistory'

describe('ResultList', () => {
  it('says when there is nothing yet', () => {
    render(<ResultList results={[]} onShow={vi.fn()} />)
    expect(screen.getByText('Nenhum resultado ainda')).toBeInTheDocument()
  })

  it('lists results and shows one again', () => {
    const onShow = vi.fn()
    const report = resultView({
      id: 8,
      title: 'Filtro por bairro',
      report: 'x',
      files: [],
      changes: [
        { path: 'a.ts', added: 61, removed: 6 },
        { path: 'b.ts', added: 8, removed: 2 },
      ],
    })
    render(<ResultList results={[report, resultView()]} onShow={onShow} />)

    fireEvent.click(screen.getByRole('button', { name: /Filtro por bairro/ }))
    expect(onShow).toHaveBeenCalledWith(8)
    expect(screen.getByText('+69')).toBeInTheDocument()
  })

  it('greys out a result whose files are gone', () => {
    const gone = resultView({ files: [{ name: 'x.webm', kind: 'video', size: 0, exists: false }] })
    render(<ResultList results={[gone]} onShow={vi.fn()} />)
    expect(screen.getByText(/Arquivo não existe mais/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Design fez o retrato/ })).not.toBeInTheDocument()
  })
})
