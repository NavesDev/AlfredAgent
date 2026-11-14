import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { Folder, GitBranch, Plus } from '../../../components/icons'
import { button, card, PageShell, primaryButton } from '../../../components/layout/PageShell'
import { field } from '../../../lib/sessionForm'
import { ProjectMark } from '../components/ProjectMark'
import { useProjectActions, useProjects, useSessionList } from '../hooks/useProjects'

export function ProjectsPage() {
  const { projects, loading } = useProjects()
  const sessions = useSessionList()
  const [creating, setCreating] = useState(false)
  const showForm = creating || (!loading && projects.length === 0)

  return (
    <PageShell
      title="Projetos"
      subtitle={
        !loading &&
        `${projects.length} ${projects.length === 1 ? 'projeto' : 'projetos'} · ${sessions.filter((s) => s.project).length} sessões`
      }
      actions={
        !showForm && (
          <button onClick={() => setCreating(true)} className={primaryButton}>
            <Plus className="size-3.5" />
            Novo projeto
          </button>
        )
      }
    >
      {showForm && (
        <CreateProject onDone={() => setCreating(false)} cancelable={projects.length > 0} />
      )}

      {!loading && projects.length === 0 && (
        <p className="text-center text-sm text-gray-500">
          Um projeto agrupa ambientes (pastas) e sessões. Por voz: “Alfred, cria o projeto Recurve”.
        </p>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {projects.map((p) => {
          const mine = sessions.filter((s) => s.project === p.name)
          const busy = mine.filter((s) => s.status === 'busy').length
          return (
            <li key={p.id}>
              <Link
                to={`/projects/${p.id}`}
                className={`${card} group flex h-full flex-col gap-4 transition hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.04]`}
              >
                <div className="flex items-start gap-3">
                  <ProjectMark name={p.name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-gray-100">{p.name}</p>
                    <p className="truncate text-xs text-gray-500">
                      {p.aliases.length ? p.aliases.join(', ') : 'sem apelidos'}
                    </p>
                  </div>
                  {busy > 0 && (
                    <span className="flex items-center gap-1.5 rounded-full bg-emerald-400/10 px-2 py-0.5 text-[11px] text-emerald-300">
                      <span className="size-1.5 animate-pulse rounded-full bg-emerald-300" />
                      {busy} ativa{busy > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {p.workspaces.slice(0, 4).map((w) => (
                    <span
                      key={w.id}
                      className="inline-flex items-center gap-1 rounded-md border border-white/5 bg-white/[0.03] px-1.5 py-0.5 text-[11px] text-gray-400"
                    >
                      {w.parent_id ? (
                        <GitBranch className="size-3" />
                      ) : (
                        <Folder className="size-3" />
                      )}
                      {w.name}
                    </span>
                  ))}
                  {p.workspaces.length > 4 && (
                    <span className="px-1 text-[11px] text-gray-500">
                      +{p.workspaces.length - 4}
                    </span>
                  )}
                  {p.workspaces.length === 0 && (
                    <span className="text-[11px] text-gray-600">nenhum ambiente</span>
                  )}
                </div>
                <div className="mt-auto flex items-center gap-3 border-t border-white/5 pt-3 text-xs text-gray-500">
                  <span>
                    {p.workspaces.length} {p.workspaces.length === 1 ? 'ambiente' : 'ambientes'}
                  </span>
                  <span>{mine.length} sessões</span>
                  <span className="ml-auto text-gray-600 transition group-hover:translate-x-0.5 group-hover:text-gray-300">
                    →
                  </span>
                </div>
              </Link>
            </li>
          )
        })}
      </ul>
    </PageShell>
  )
}

function CreateProject({ onDone, cancelable }: { onDone: () => void; cancelable: boolean }) {
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
      { onSuccess: () => (setName(''), setAliases(''), onDone()) },
    )
  }

  return (
    <form onSubmit={submit} className={`${card} flex flex-col gap-3`}>
      <div className="flex items-center gap-3">
        <ProjectMark name={name.trim() || '?'} />
        <div>
          <p className="text-sm font-medium text-gray-100">Novo projeto</p>
          <p className="text-xs text-gray-500">
            Apelidos ajudam o Alfred a reconhecer o nome falado.
          </p>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <input
          aria-label="Nome do projeto"
          placeholder="nome (ex: Recurve)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={field}
          autoFocus
        />
        <input
          aria-label="Apelidos"
          placeholder="apelidos, separados por vírgula"
          value={aliases}
          onChange={(e) => setAliases(e.target.value)}
          className={field}
        />
      </div>
      {create.error && <p className="text-xs text-red-300">{create.error.message}</p>}
      <div className="flex justify-end gap-2">
        {cancelable && (
          <button type="button" onClick={onDone} className={button}>
            Cancelar
          </button>
        )}
        <button className={primaryButton} disabled={!name.trim() || create.isPending}>
          Criar projeto
        </button>
      </div>
    </form>
  )
}
