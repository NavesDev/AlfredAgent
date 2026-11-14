import { useState, type FormEvent } from 'react'
import { Plus } from '../../../components/icons'
import { button, card, PageShell, primaryButton } from '../../../components/layout/PageShell'
import { field } from '../../../lib/sessionForm'
import { MAX_DESCRIPTION } from '../components/Description'
import { ProjectCard } from '../components/ProjectCard'
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
        <p className="text-center text-sm text-ink-3">
          Um projeto agrupa ambientes (pastas) e sessões. Por voz: “Alfred, cria o projeto Recurve”.
        </p>
      )}

      <ul className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
        {projects.map((p) => (
          <li key={p.id} className="grid">
            <ProjectCard project={p} sessions={sessions.filter((s) => s.project === p.name)} />
          </li>
        ))}
        {projects.length > 0 && !showForm && (
          <li className="grid">
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="grid min-h-56 place-content-center justify-items-center gap-1.5 rounded-card p-6 text-center shadow-[inset_0_0_0_1.5px_rgba(255,255,255,0.14)] transition hover:bg-fill"
            >
              <span className="grid size-12 place-items-center rounded-full bg-fill">
                <Plus className="size-5" />
              </span>
              <span className="font-semibold">Novo projeto</span>
              <span className="text-xs text-ink-3">Ou diga: “Alfred, cria o projeto Recurve”</span>
            </button>
          </li>
        )}
      </ul>
    </PageShell>
  )
}

function CreateProject({ onDone, cancelable }: { onDone: () => void; cancelable: boolean }) {
  const { create } = useProjectActions()
  const [name, setName] = useState('')
  const [aliases, setAliases] = useState('')
  const [description, setDescription] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    create.mutate(
      {
        name: name.trim(),
        aliases: aliases
          .split(',')
          .map((a) => a.trim())
          .filter(Boolean),
        description: description.trim(),
      },
      { onSuccess: () => (setName(''), setAliases(''), setDescription(''), onDone()) },
    )
  }

  return (
    <form onSubmit={submit} className={`${card} flex flex-col gap-3`}>
      <div className="flex items-center gap-3">
        <ProjectMark name={name.trim() || '?'} />
        <div>
          <p className="text-sm font-medium text-ink">Novo projeto</p>
          <p className="text-xs text-ink-3">Apelidos ajudam o Alfred a reconhecer o nome falado.</p>
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
        <input
          aria-label="Descrição do projeto"
          placeholder="descrição curta (opcional): do que o projeto trata"
          value={description}
          maxLength={MAX_DESCRIPTION}
          onChange={(e) => setDescription(e.target.value)}
          className={`${field} sm:col-span-2`}
        />
      </div>
      {create.error && <p className="text-xs text-[#ff9a92]">{create.error.message}</p>}
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
