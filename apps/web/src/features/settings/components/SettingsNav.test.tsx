// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SettingsNav } from './SettingsNav'

describe('SettingsNav', () => {
  it('marks the open section and opens another on click', async () => {
    const onSelect = vi.fn()
    render(<SettingsNav current="modelos" onSelect={onSelect} />)
    expect(screen.getByRole('link', { name: 'Modelos' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'MCPs' })).toHaveAttribute('href', '#mcps')
    await userEvent.setup().click(screen.getByRole('link', { name: 'MCPs' }))
    expect(onSelect).toHaveBeenCalledWith('mcps')
  })
})
