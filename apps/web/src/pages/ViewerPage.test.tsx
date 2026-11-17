// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { resultView } from '../features/results/lib/fixtures'
import { ViewerPage } from './ViewerPage'

vi.mock('../lib/desktop', () => ({ isDesktop: () => false, appWindow: vi.fn() }))

function renderAt(url: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <ViewerPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('ViewerPage', () => {
  it('closes itself for an id that is not a result', async () => {
    const close = vi.spyOn(window, 'close').mockImplementation(() => {})
    renderAt('/viewer?id=abc&i=0')
    await waitFor(() => expect(close).toHaveBeenCalled())
  })

  it('closes itself when the result is unknown', async () => {
    const close = vi.spyOn(window, 'close').mockImplementation(() => {})
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('{}', { status: 404 })),
    )
    renderAt('/viewer?id=99&i=0')
    await waitFor(() => expect(close).toHaveBeenCalled())
  })

  it('shows the result on the slide asked for', async () => {
    const result = resultView({ id: 5, report: 'Mudou o filtro', files: [] })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify(result), { status: 200 })),
    )
    renderAt('/viewer?id=5&i=0')
    expect(await screen.findByRole('region', { name: result.title })).toBeInTheDocument()
  })
})
