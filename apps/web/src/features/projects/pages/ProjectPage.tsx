import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router'
import type { Workspace } from '../../../api/events'
import { button, card, PageShell } from '../../../components/layout/PageShell'
import { NewSessionForm } from '../../../components/NewSessionForm'
import { field } from '../../../lib/sessionForm'
import { useProjectActions, useProjects, useSessionList } from '../hooks/useProjects'

export function ProjectPage() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const { projects, loading } = useProjects()
  const sessions = useSessionList()
  const actions = useProjectActions()
  const project = projects.find((p) => p.id === id)

  if (!project) {
    return (
      <PageShell title="Projeto">
        {!loading && <p className="text-sm text-gray-500">Projeto não encontrado.</p>}
      </PageShell>
    )
  }

  const mine = sessions.filter((s) => s.project === project.name)
  const removeProject = () =>
    actions.remove.mutate(project.id, { onSuccess: () => navigate('/projects') })

  return (
    <PageShell
      title={
        <span className="flex items-center gap-3">
          <span className="size-3 rotate-45 border border-gray-300" />
          {project.name}
          {project.aliases.length > 0 && (
            <span className="text-sm font-normal text-gray-500">{project.aliases.join(', ')}</span>
          )}
        </span>
      }
    >
      <section className={card}>
        <h3 className="mb-3 text-sm font-medium text-gray-200">Workspaces</h3>
        <ul className="mb-4 flex flex-col gap-1.5">
          {project.workspaces.map((w) => (
            <WorkspaceRow
              key={w.id}
              workspace={w}
              workspaces={project.workspaces}
              sessions={mine.filter((s) => s.workspace === w.name).map((s) => s.name)}
            />
          ))}
          {project.workspaces.length === 0 && (
            <li className="text-xs text-gray-500">Nenhum workspace.</li>
          )}
        </ul>
        <AddWorkspace projectId={project.id} workspaces={project.workspaces} />
      </section>

      <section className={card}>
        <h3 className="mb-3 text-sm font-medium text-gray-200">Sessões</h3>
        <ul className="mb-4 flex flex-col gap-1 text-sm">
          {mine.map((s) => (
            <li key={s.name} className="flex gap-2 text-gray-300">
              <span className="text-gray-100">{s.name}</span>
              <span className="text-gray-500">
                {s.label} · {s.workspace} · {s.model}
                {s.effort ? ` · ${s.effort}` : ''} ·{' '}
                {s.status === 'busy' ? 'ocupada' : s.status === 'error' ? 'erro' : 'livre'}
              </span>
            </li>
          ))}
          {mine.length === 0 && <li className="text-xs text-gray-500">Nenhuma sessão.</li>}
        </ul>
        {project.workspaces.length > 0 && (
          <NewSessionForm
            key={mine.length}
            projects={projects}
            projectId={project.id}
            pending={actions.createSession.isPending}
            error={actions.createSession.error?.message}
            onSubmit={(body) => actions.createSession.mutate(body)}
          />
        )}
      </section>

      <section className="flex items-center gap-3">
        <button
          onClick={removeProject}
          className={`${button} text-red-300`}
          disabled={actions.remove.isPending}
        >
          Apagar projeto
        </button>
        {actions.remove.error && (
          <p className="text-xs text-red-300">{actions.remove.error.message}</p>
        )}
      </section>
    </PageShell>
  )
}

function WorkspaceRow({
  workspace: w,
  workspaces,
  sessions,
}: {
  workspace: Workspace
  workspaces: Workspace[]
  sessions: string[]
}) {
  const { removeWorkspace } = useProjectActions()
  const [confirm, setConfirm] = useState<'no' | 'yes' | 'force'>('no')
  const parent = workspaces.find((p) => p.id === w.parent_id)
  const dirty = removeWorkspace.error?.message.includes('não commitadas')

  const onDelete = () => {
    if (confirm === 'no') return setConfirm(dirty ? 'force' : 'yes')
    removeWorkspace.mutate(
      { id: w.id, force: confirm === 'force' },
      { onError: () => setConfirm('no') },
    )
  }

  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-white/5 px-3 py-2 text-sm">
      <span className="text-gray-100">{w.name}</span>
      <span className="font-mono text-xs text-gray-500">{w.path}</span>
      {w.branch && <span className="text-xs text-gray-400">⎇ {w.branch}</span>}
      {parent && <span className="text-xs text-gray-500">worktree de {parent.name}</span>}
      {sessions.length > 0 && (
        <span className="text-xs text-gray-400">sessões: {sessions.join(', ')}</span>
      )}
      <button onClick={onDelete} className="ml-auto text-xs text-red-300 hover:text-red-200">
        {confirm === 'no'
          ? 'Apagar'
          : confirm === 'force'
            ? 'Forçar (perde mudanças)'
            : 'Confirmar'}
      </button>
      {removeWorkspace.error && (
        <p className="w-full text-xs text-red-300">{removeWorkspace.error.message}</p>
      )}
    </li>
  )
}

function AddWorkspace({ projectId, workspaces }: { projectId: number; workspaces: Workspace[] }) {
  const { addWorkspace, addWorktree } = useProjectActions()
  const [mode, setMode] = useState<'folder' | 'worktree'>('folder')
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [picked, setParent] = useState<number | null>(null)
  const parent = picked ?? workspaces[0]?.id ?? null
  const pending = addWorkspace.isPending || addWorktree.isPending
  const error = addWorkspace.error ?? addWorktree.error
  const done = () => (setName(''), setPath(''))

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (mode === 'folder')
      addWorkspace.mutate(
        { id: projectId, name: name.trim(), path: path.trim() },
        { onSuccess: done },
      )
    else if (parent !== null)
      addWorktree.mutate(
        { id: projectId, parent_id: parent, name: name.trim() },
        { onSuccess: done },
      )
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
      <select
        aria-label="Tipo de workspace"
        value={mode}
        onChange={(e) => setMode(e.target.value as 'folder' | 'worktree')}
        className={field}
      >
        <option value="folder">pasta</option>
        <option value="worktree" disabled={!workspaces.length}>
          git worktree
        </option>
      </select>
      <input
        aria-label="Nome do workspace"
        placeholder="nome (ex: back)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className={`${field} w-32`}
      />
      {mode === 'folder' ? (
        <input
          aria-label="Pasta"
          placeholder="~/dev/recurve-api"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          className={`${field} min-w-40 flex-1 font-mono`}
        />
      ) : (
        <select
          aria-label="A partir de"
          value={parent ?? ''}
          onChange={(e) => setParent(Number(e.target.value))}
          className={`${field} flex-1`}
        >
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>
              a partir de {w.name}
            </option>
          ))}
        </select>
      )}
      <button
        className={button}
        disabled={pending || !name.trim() || (mode === 'folder' ? !path.trim() : parent === null)}
      >
        Adicionar
      </button>
      {error && <p className="w-full text-xs text-red-300">{error.message}</p>}
    </form>
  )
}
