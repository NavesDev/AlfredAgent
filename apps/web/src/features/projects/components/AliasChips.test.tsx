// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AliasChips } from './AliasChips'

const setup = () => {
  const onChange = vi.fn()
  render(<AliasChips aliases={['vrumi', 'vrummi']} onChange={onChange} />)
  return { onChange, user: userEvent.setup() }
}

describe('AliasChips', () => {
  it('removes an alias', async () => {
    const { onChange, user } = setup()
    await user.click(screen.getByRole('button', { name: 'Tirar apelido vrumi' }))
    expect(onChange).toHaveBeenCalledWith(['vrummi'])
  })

  it('adds a new alias, ignoring blanks and repeats', async () => {
    const { onChange, user } = setup()
    await user.click(screen.getByRole('button', { name: 'Apelido' }))
    await user.type(screen.getByRole('textbox', { name: 'Novo apelido' }), ' vrumy {Enter}')
    expect(onChange).toHaveBeenCalledWith(['vrumi', 'vrummi', 'vrumy'])

    onChange.mockClear()
    await user.click(screen.getByRole('button', { name: 'Apelido' }))
    await user.type(screen.getByRole('textbox', { name: 'Novo apelido' }), 'VRUMI{Enter}')
    expect(onChange).not.toHaveBeenCalled()
  })
})
