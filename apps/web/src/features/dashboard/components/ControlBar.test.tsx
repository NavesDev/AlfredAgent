// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ControlBar } from './ControlBar'

const setup = (over: Partial<Parameters<typeof ControlBar>[0]> = {}) => {
  const props = {
    state: 'idle' as const,
    family: 'sonnet' as const,
    onFamily: vi.fn(),
    onNewConversation: vi.fn(),
    transcript: false,
    onTranscript: vi.fn(),
    ...over,
  }
  render(<ControlBar {...props} />)
  return { ...props, user: userEvent.setup() }
}

describe('ControlBar', () => {
  it('says what Alfred is doing and how to call him', () => {
    setup()
    expect(screen.getByText('Em espera')).toBeInTheDocument()
    expect(screen.getByText('Diga “Alfred”')).toBeInTheDocument()
  })

  it("switches Alfred's model family", async () => {
    const { onFamily, user } = setup()
    expect(screen.getByRole('radio', { name: 'Sonnet' })).toHaveAttribute('aria-checked', 'true')
    await user.click(screen.getByRole('radio', { name: 'Opus' }))
    expect(onFamily).toHaveBeenCalledWith('opus')
  })

  it('starts a new conversation and toggles the transcript', async () => {
    const { onNewConversation, onTranscript, user } = setup({ transcript: true })
    await user.click(screen.getByRole('button', { name: 'Nova conversa' }))
    expect(onNewConversation).toHaveBeenCalledOnce()
    const toggle = screen.getByRole('button', { name: 'Transcrição' })
    expect(toggle).toHaveAttribute('aria-pressed', 'true')
    await user.click(toggle)
    expect(onTranscript).toHaveBeenCalledOnce()
  })
})
