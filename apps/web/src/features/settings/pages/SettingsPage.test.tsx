// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { SettingsView } from '../../../api/events'
import { Form } from './SettingsPage'

const settings: SettingsView = {
  agents: [],
  max_active_sessions: 3,
  idle_minutes: 10,
  mcp_disabled: [],
  image_mcp: null,
  image_mcp_servers: [],
  known_mcp_servers: [],
  implementation_mode: 'worktree',
  overlay_position: 'top_right',
}

describe('Settings form, sessions section', () => {
  it('saves the global feature mode', () => {
    const save = { mutate: vi.fn(), isPending: false, isSuccess: false, error: null }
    render(<Form settings={settings} save={save as never} section="sessoes" />)

    fireEvent.click(screen.getByRole('radio', { name: 'No próprio ambiente' }))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(save.mutate).toHaveBeenCalledWith(
      expect.objectContaining({ implementation_mode: 'ambiente' }),
    )
  })
})

describe('Settings form, general section', () => {
  it('saves where the pill and the card float', () => {
    const save = { mutate: vi.fn(), isPending: false, isSuccess: false, error: null }
    render(<Form settings={settings} save={save as never} section="geral" />)

    expect(screen.getByRole('img', { name: 'Em cima à direita' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Posição da pílula' }))
    fireEvent.click(screen.getByRole('option', { name: /Embaixo no centro/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(save.mutate).toHaveBeenCalledWith(
      expect.objectContaining({ overlay_position: 'bottom_center' }),
    )
    expect(screen.getByRole('img', { name: 'Embaixo no centro' })).toBeInTheDocument()
  })
})
