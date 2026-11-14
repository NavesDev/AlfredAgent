// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { UsageRing } from './UsageRing'

describe('UsageRing', () => {
  it('shows the share used with its window and when it resets', () => {
    render(<UsageRing percent={38} tone="ok" label="Janela de 5 horas" note="renova em 2 h" />)
    expect(screen.getByRole('meter', { name: 'Janela de 5 horas' })).toHaveAttribute(
      'aria-valuenow',
      '38',
    )
    expect(screen.getByText('38%')).toBeInTheDocument()
    expect(screen.getByText('renova em 2 h')).toBeInTheDocument()
  })

  it('shows a dash before the first reading', () => {
    render(<UsageRing percent={null} tone="ok" label="Semana" />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
