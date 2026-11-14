import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router'
import type { SessionView, Workspace } from '../../../api/events'
import { Segmented } from '../../../components/controls'
import { Folder, GitBranch, Plus, Terminal, Trash } from '../../../components/icons'
import {
  button,
  card,
  dangerButton,
  PageShell,
  primaryButton,
} from '../../../components/layout/PageShell'
import { NewSessionForm } from '../../../components/NewSessionForm'
import { field } from '../../../lib/sessionForm'
import { ProjectMark } from '../components/ProjectMark'
import { useProjectActions, useProjects, useSessionList } from '../hooks/useProjects'

const BACK = { to: '/projects', label: 'Projetos' }
const STATUS: Record<SessionView['status'], { label: string; dot: string }> = {
  busy: { label: 'ocupada', dot: 'bg-emerald-300 animate-pulse' },
  error: { label: 'erro', dot: 'bg-red-400' },
  idle: { label: 'livre', dot: 'bg-gray-500' },
}

export function ProjectPage() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const { projects, loading } = useProjects()
  const sessions = useSessionList()
  const actions = useProjectActions()
  const [newSession, setNewSession] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const project = projects.find((p) => p.id === id)

  if (!project) {
    return (
      <PageShell title="Projeto" back={BACK}>
        {!loading && <p className="text-sm text-gray-500">Projeto não encontrado.</p>}
      </PageShell>
    )
  }

  const mine = sessions.filter((s) => s.project === project.name)
  const removeProject = () =>
    actions.remove.mutate(project.id, { onSuccess: () => navigate('/projects') })

  return (
    <PageShell
      back={BACK}
      title={
        <span className="flex items-center gap-3">
          <ProjectMark name={project.name} size="lg" />
          <span className="flex flex-col">
            {project.name}
            <span className="flex flex-wrap gap-1 pt-1 text-xs font-normal">
              {project.aliases.map((a) => (
                <span key={a} className="rounded-full bg-white/5 px-2 py-0.5 text-gray-400">
                  {a}
                </span>
              ))}
              <span className="py-0.5 text-gray-500">
                {project.workspaces.length}{' '}
                {project.workspaces.length === 1 ? 'ambiente' : 'ambientes'} · {mine.length} sessões
              </span>
            </span>
          </span>
        </span>
      }
    >
      <section className="flex flex-col gap-2.5">
        <h3 className="text-sm font-medium text-gray-200">Ambientes</h3>
        <ul className="divide-y divide-white/5 rounded-xl border border-white/10 bg-white/[0.02]">
          {project.workspaces.map((w) => (
            <WorkspaceRow
              key={w.id}
              workspace={w}
              workspaces={project.workspaces}
              sessions={mine.filter((s) => s.workspace === w.name).map((s) => s.name)}
            />
          ))}
          {project.workspaces.length === 0 && (
            <li className="px-4 py-3.5 text-xs text-gray-500">
              Nenhum ambiente. Adicione a pasta do repositório abaixo.
            </li>
          )}
          <li className="px-4 py-3.5">
            <AddWorkspace projectId={project.id} workspaces={project.workspaces} />
          </li>
        </ul>
      </section>

      <section className="flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-200">Sessões</h3>
          {project.workspaces.length > 0 && !newSession && (
            <button onClick={() => setNewSession(true)} className={button}>
              <Plus className="size-3.5" />
              Nova sessão
            </button>
          )}
        </div>
        {newSession && (
          <div className={card}>
            <NewSessionForm
              projects={projects}
              projectId={project.id}
              pending={actions.createSession.isPending}
              error={actions.createSession.error?.message}
              onSubmit={(body) =>
                actions.createSession.mutate(body, { onSuccess: () => setNewSession(false) })
              }
              onCancel={() => setNewSession(false)}
            />
          </div>
        )}
        <ul className="divide-y divide-white/5 rounded-xl border border-white/10 bg-white/[0.02]">
          {mine.map((s) => (
            <li key={s.name} className="flex items-center gap-3 px-4 py-3">
              <span className="grid size-7 shrink-0 place-items-center rounded-lg border border-white/10 bg-white/[0.03] text-gray-400">
                <Terminal />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-gray-100">{s.name}</p>
                <p className="truncate text-xs text-gray-500">
                  {s.label} · {s.workspace}
                </p>
              </div>
              <span className="hidden rounded-md border border-white/5 bg-white/[0.03] px-1.5 py-0.5 font-mono text-[11px] text-gray-400 sm:inline">
                {s.model}
                {s.effort ? ` · ${s.effort}` : ''}
              </span>
              <span className="flex w-16 items-center gap-1.5 text-xs text-gray-400">
                <span className={`size-1.5 rounded-full ${STATUS[s.status].dot}`} />
                {STATUS[s.status].label}
              </span>
            </li>
          ))}
          {mine.length === 0 && (
            <li className="px-4 py-3.5 text-xs text-gray-500">
              {project.workspaces.length
                ? 'Nenhuma sessão ainda.'
                : 'Crie um ambiente antes de abrir sessões.'}
            </li>
          )}
        </ul>
      </section>

      <section className="flex flex-col gap-3 rounded-xl border border-red-400/15 bg-red-400/[0.03] px-4 py-3.5 sm:flex-row sm:items-center">
        <div className="flex-1">
          <p className="text-sm text-gray-100">Apagar projeto</p>
          <p className="text-xs text-gray-500">
            Remove o projeto e seus ambientes do Alfred. As pastas no disco ficam.
          </p>
          {actions.remove.error && (
            <p className="mt-1 text-xs text-red-300">{actions.remove.error.message}</p>
          )}
        </div>
        <div className="flex gap-2">
          {confirmDelete && (
            <button onClick={() => setConfirmDelete(false)} className={button}>
              Cancelar
            </button>
          )}
          <button
            onClick={confirmDelete ? removeProject : () => setConfirmDelete(true)}
            className={dangerButton}
            disabled={actions.remove.isPending}
          >
            <Trash className="size-3.5" />
            {confirmDelete ? 'Confirmar exclusão' : 'Apagar'}
          </button>
        </div>
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
    <li className="group flex flex-wrap items-center gap-3 px-4 py-3">
      <span className="grid size-7 shrink-0 place-items-center rounded-lg border border-white/10 bg-white/[0.03] text-gray-400">
        {parent ? <GitBranch /> : <Folder />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 text-sm text-gray-100">
          {w.name}
          {w.branch && (
            <span className="rounded-md bg-sky-400/10 px-1.5 py-0.5 font-mono text-[11px] text-sky-300">
              {w.branch}
            </span>
          )}
          {parent && <span className="text-xs text-gray-500">worktree de {parent.name}</span>}
        </p>
        <p className="truncate font-mono text-xs text-gray-500">{w.path}</p>
      </div>
      {sessions.length > 0 && (
        <span className="text-xs text-gray-400" title={sessions.join(', ')}>
          {sessions.length} {sessions.length === 1 ? 'sessão' : 'sessões'}
        </span>
      )}
      <div className="flex gap-1.5">
        {confirm !== 'no' && (
          <button onClick={() => setConfirm('no')} className={button}>
            Cancelar
          </button>
        )}
        <button
          onClick={onDelete}
          aria-label={`Apagar ambiente ${w.name}`}
          className={
            confirm === 'no'
              ? 'grid size-7 place-items-center rounded-lg text-gray-500 opacity-60 transition group-hover:opacity-100 hover:bg-red-400/10 hover:text-red-300'
              : dangerButton
          }
        >
          {confirm === 'no' ? (
            <Trash className="size-3.5" />
          ) : confirm === 'force' ? (
            'Forçar (perde mudanças)'
          ) : (
            'Confirmar'
          )}
        </button>
      </div>
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
    <form onSubmit={submit} className="flex flex-col gap-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-gray-400">Adicionar ambiente</p>
        <Segmented
          label="Tipo de ambiente"
          value={mode}
          onChange={setMode}
          options={[
            { value: 'folder', label: 'Pasta' },
            { value: 'worktree', label: 'Git worktree', disabled: !workspaces.length },
          ]}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <input
          aria-label="Nome do ambiente"
          placeholder="nome (ex: back)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={`${field} w-36`}
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
            className={`${field} min-w-40 flex-1`}
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                a partir de {w.name}
              </option>
            ))}
          </select>
        )}
        <button
          className={primaryButton}
          disabled={pending || !name.trim() || (mode === 'folder' ? !path.trim() : parent === null)}
        >
          <Plus className="size-3.5" />
          Adicionar
        </button>
      </div>
      {error && <p className="text-xs text-red-300">{error.message}</p>}
    </form>
  )
}
