import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { button, card, PageShell } from '../../../components/layout/PageShell'
import { field } from '../../../lib/sessionForm'
import { useProjectActions, useProjects, useSessionList } from '../hooks/useProjects'

export function ProjectsPage() {
  const { projects, loading } = useProjects()
  const sessions = useSessionList()
  const { create } = useProjectActions()
  const [name, setName] = useState('')
  const [aliases, setAliases] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    create.mutate(
      {
        name: name.trim(),
        aliases: aliases
          .split(',')
          .map((a) => a.trim())
          .filter(Boolean),
      },
      { onSuccess: () => (setName(''), setAliases('')) },
    )
  }

  return (
    <PageShell title="Projetos">
      <form onSubmit={submit} className={`${card} flex flex-wrap items-center gap-2`}>
        <input
          aria-label="Nome do projeto"
          placeholder="novo projeto (ex: Recurve)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={`${field} min-w-40 flex-1`}
        />
        <input
          aria-label="Apelidos"
          placeholder="apelidos, separados por vírgula"
          value={aliases}
          onChange={(e) => setAliases(e.target.value)}
          className={`${field} min-w-40 flex-1`}
        />
        <button className={button} disabled={!name.trim() || create.isPending}>
          Criar projeto
        </button>
        {create.error && <p className="w-full text-xs text-red-300">{create.error.message}</p>}
      </form>

      {!loading && projects.length === 0 && (
        <p className="text-sm text-gray-500">
          Nenhum projeto ainda. Um projeto agrupa pastas (workspaces) e sessões; por voz: “Alfred,
          cria o projeto Recurve”.
        </p>
      )}
      <ul className="flex flex-col gap-2">
        {projects.map((p) => {
          const count = sessions.filter((s) => s.project === p.name).length
          return (
            <li key={p.id}>
              <Link
                to={`/projects/${p.id}`}
                className={`${card} flex items-center gap-3 hover:border-white/20`}
              >
                <span className="size-2.5 rotate-45 border border-gray-400" />
                <span className="font-medium text-gray-100">{p.name}</span>
                {p.aliases.length > 0 && (
                  <span className="text-xs text-gray-500">{p.aliases.join(', ')}</span>
                )}
                <span className="ml-auto text-xs text-gray-400">
                  {p.workspaces.length} workspaces · {count} sessões
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </PageShell>
  )
}
