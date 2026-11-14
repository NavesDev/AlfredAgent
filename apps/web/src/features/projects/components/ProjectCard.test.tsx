// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import type { Project } from '../../../api/events'
import { sessionView } from '../../../lib/sessionView'
import { ProjectCard } from './ProjectCard'

const ws = (id: number, name: string) => ({
  id,
  project_id: 1,
  name,
  path: `/p/${name}`,
  kind: 'folder' as const,
  description: '',
})
const vrummy: Project = {
  id: 1,
  name: 'Vrummy',
  aliases: ['vrumi'],
  description: 'Aluguel de carros entre pessoas',
  workspaces: [ws(1, 'principal'), ws(2, 'design')],
}

const show = (sessions = [sessionView('Developer', { project: 'Vrummy', status: 'busy' })]) =>
  render(
    <MemoryRouter>
      <ProjectCard project={vrummy} sessions={sessions} />
    </MemoryRouter>,
  )

describe('ProjectCard', () => {
  it('links to the project with its description, aliases and counts', () => {
    show()
    const link = screen.getByRole('link', { name: /Vrummy/ })
    expect(link).toHaveAttribute('href', '/projects/1')
    expect(link).toHaveTextContent('Aluguel de carros entre pessoas')
    expect(link).toHaveTextContent('Também: vrumi')
    expect(link).toHaveTextContent('2 ambientes · 1 sessão')
  })

  it('flags sessions that are working', () => {
    show()
    expect(screen.getByText('1 trabalhando')).toBeInTheDocument()
  })

  it('stays quiet when nothing is running', () => {
    show([sessionView('Design', { project: 'Vrummy' })])
    expect(screen.queryByText(/trabalhando/)).not.toBeInTheDocument()
  })
})
