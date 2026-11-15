// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TitleBar } from './TitleBar'

describe('TitleBar', () => {
  it('offers the three window buttons by name', () => {
    render(<TitleBar connection="open" />)
    for (const name of ['Minimizar', 'Maximizar', 'Fechar'])
      expect(screen.getByRole('button', { name })).toBeInTheDocument()
  })

  it('lets the empty bar drag the window', () => {
    render(<TitleBar connection="open" />)
    expect(screen.getByRole('banner')).toHaveAttribute('data-tauri-drag-region')
  })
})
