// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { NavRail } from './NavRail'

const at = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <NavRail connection="open" />
    </MemoryRouter>,
  )

describe('NavRail', () => {
  it('links the three sections by name', () => {
    at('/')
    for (const name of ['Painel', 'Projetos', 'Configurações'])
      expect(screen.getByRole('link', { name })).toBeInTheDocument()
  })

  it('marks the section of the current page, including a project inside Projetos', () => {
    at('/projects/3')
    expect(screen.getByRole('link', { name: 'Projetos' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Painel' })).not.toHaveAttribute('aria-current')
  })

  it('says whether the server is connected', () => {
    at('/')
    expect(screen.getByRole('status')).toHaveAccessibleName('Servidor conectado')
  })
})
