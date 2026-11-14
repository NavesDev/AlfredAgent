import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router'
import type { Workspace } from '../../../api/events'
import { Segmented, Section } from '../../../components/controls'
import { Folder, GitBranch, Plus, Trash } from '../../../components/icons'
import {
  button,
  card,
  dangerButton,
  PageShell,
  primaryButton,
} from '../../../components/layout/PageShell'
import { NewSessionForm } from '../../../components/NewSessionForm'
import { SessionPhoto } from '../../../components/SessionPhoto'
import { presence } from '../../../lib/presence'
import { field } from '../../../lib/sessionForm'
import { AliasChips } from '../components/AliasChips'
import { Description, MAX_DESCRIPTION } from '../components/Description'
import { ProjectMark } from '../components/ProjectMark'
import { useProjectActions, useProjects, useSessionList } from '../hooks/useProjects'
import { plural } from '../lib/projects'

const BACK = { to: '/projects', label: 'Projetos' }

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
        {!loading && <p className="text-sm text-ink-3">Projeto não encontrado.</p>}
      </PageShell>
    )
  }

  const mine = sessions.filter((s) => s.project === project.name)
  const worktrees = project.workspaces.filter((w) => w.kind === 'worktree').length
  const removeProject = () =>
    actions.remove.mutate(project.id, { onSuccess: () => navigate('/projects') })

  const aside = (
    <>
      <div className="flex flex-col items-center gap-1.5 text-center">
        <ProjectMark name={project.name} size="lg" />
        <h2 className="mt-1.5 text-[22px] font-bold tracking-tight">{project.name}</h2>
        <p className="text-xs text-ink-2">
          {plural(project.workspaces.length, 'ambiente', 'ambientes')}
          {worktrees > 0 && ` · ${plural(worktrees, 'worktree', 'worktrees')}`} ·{' '}
          {plural(mine.length, 'sessão', 'sessões')}
        </p>
        <div className="max-w-[30ch] text-sm">
          <Description
            value={project.description}
            label="Descrição do projeto"
            pending={actions.update.isPending}
            error={actions.update.error?.message}
            onSave={(description) => actions.update.mutate({ id: project.id, description })}
          />
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="text-xs font-semibold tracking-wide text-ink-2 uppercase">Nomes falados</h3>
        <AliasChips
          aliases={project.aliases}
          pending={actions.update.isPending}
          onChange={(aliases) => actions.update.mutate({ id: project.id, aliases })}
        />
        <p className="text-xs text-ink-3">O Alfred entende o projeto por esses nomes.</p>
      </div>
      <div className="mt-auto flex flex-col gap-2">
        {actions.remove.error && (
          <p className="text-xs text-[#ff9a92]">{actions.remove.error.message}</p>
        )}
        <div className="flex gap-2">
          {confirmDelete && (
            <button onClick={() => setConfirmDelete(false)} className={`${button} flex-1`}>
              Cancelar
            </button>
          )}
          <button
            onClick={confirmDelete ? removeProject : () => setConfirmDelete(true)}
            className={`${dangerButton} flex-1`}
            disabled={actions.remove.isPending}
            title="Remove o projeto e seus ambientes do Alfred. As pastas no disco ficam."
          >
            <Trash className="size-3.5" />
            {confirmDelete ? 'Confirmar' : 'Apagar projeto'}
          </button>
        </div>
      </div>
    </>
  )

  return (
    <PageShell back={BACK} aside={aside}>
      <Section title="Ambientes">
        {project.workspaces.map((w) => (
          <WorkspaceRow
            key={w.id}
            workspace={w}
            workspaces={project.workspaces}
            sessions={mine.filter((s) => s.workspace === w.name)}
          />
        ))}
        {project.workspaces.length === 0 && (
          <p className="px-4 py-3.5 text-xs text-ink-3">
            Nenhum ambiente. Adicione a pasta do repositório abaixo.
          </p>
        )}
        <div className="px-4 py-3.5">
          <AddWorkspace projectId={project.id} workspaces={project.workspaces} />
        </div>
      </Section>

      <section className="flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <h3 className="text-[13px] font-semibold tracking-wide text-ink-2 uppercase">Sessões</h3>
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
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-3">
          {mine.map((s) => (
            <li
              key={s.name}
              className="grid grid-cols-[48px_minmax(0,1fr)] items-center gap-x-3 rounded-[20px] bg-well p-3"
            >
              <span className="row-span-2">
                <SessionPhoto session={s} size={48} />
              </span>
              <span className="truncate text-sm font-semibold">{s.name}</span>
              <span className="truncate text-xs text-ink-2">
                {s.workspace} · {presence(s).label}
              </span>
            </li>
          ))}
        </ul>
        {mine.length === 0 && (
          <p className="text-xs text-ink-3">
            {project.workspaces.length
              ? 'Nenhuma sessão ainda.'
              : 'Crie um ambiente antes de abrir sessões.'}
          </p>
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
  sessions: { name: string }[]
}) {
  const { removeWorkspace, updateWorkspace } = useProjectActions()
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
    <div className={`group flex flex-wrap items-center gap-3 px-4 py-3 ${parent ? 'pl-11' : ''}`}>
      <span
        className={`grid size-7 shrink-0 place-items-center rounded-lg text-white ${parent ? 'bg-apple-purple' : 'bg-apple-blue'}`}
      >
        {parent ? <GitBranch className="size-[15px]" /> : <Folder className="size-[15px]" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 text-sm">
          {w.name}
          {w.branch && (
            <span className="rounded-full bg-apple-purple/20 px-2 py-0.5 font-mono text-[11px] text-[#d9a8ff]">
              {w.branch}
            </span>
          )}
          {parent && <span className="text-xs text-ink-3">worktree de {parent.name}</span>}
        </p>
        <p className="truncate font-mono text-xs text-ink-3">{w.path}</p>
        <Description
          value={w.description}
          label={`Descrição do ambiente ${w.name}`}
          pending={updateWorkspace.isPending}
          error={updateWorkspace.error?.message}
          onSave={(description) => updateWorkspace.mutate({ id: w.id, description })}
        />
      </div>
      {sessions.length > 0 && (
        <span className="text-xs text-ink-2" title={sessions.map((s) => s.name).join(', ')}>
          {plural(sessions.length, 'sessão', 'sessões')}
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
              ? 'grid size-8 place-items-center rounded-full text-ink-3 opacity-60 transition group-hover:opacity-100 hover:bg-apple-red/15 hover:text-apple-red'
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
        <p className="w-full text-xs text-[#ff9a92]">{removeWorkspace.error.message}</p>
      )}
    </div>
  )
}

function AddWorkspace({ projectId, workspaces }: { projectId: number; workspaces: Workspace[] }) {
  const { addWorkspace, addWorktree } = useProjectActions()
  const [mode, setMode] = useState<'folder' | 'worktree'>('folder')
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [description, setDescription] = useState('')
  const [picked, setParent] = useState<number | null>(null)
  const parent = picked ?? workspaces[0]?.id ?? null
  const pending = addWorkspace.isPending || addWorktree.isPending
  const error = addWorkspace.error ?? addWorktree.error
  const done = () => (setName(''), setPath(''), setDescription(''))

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (mode === 'folder')
      addWorkspace.mutate(
        { id: projectId, name: name.trim(), path: path.trim(), description: description.trim() },
        { onSuccess: done },
      )
    else if (parent !== null)
      addWorktree.mutate(
        { id: projectId, parent_id: parent, name: name.trim(), description: description.trim() },
        { onSuccess: done },
      )
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-apple-blue">Adicionar ambiente</p>
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
        <input
          aria-label="Descrição do ambiente"
          placeholder="descrição curta (opcional)"
          value={description}
          maxLength={MAX_DESCRIPTION}
          onChange={(e) => setDescription(e.target.value)}
          className={`${field} w-full`}
        />
        <button
          className={primaryButton}
          disabled={pending || !name.trim() || (mode === 'folder' ? !path.trim() : parent === null)}
        >
          <Plus className="size-3.5" />
          Adicionar
        </button>
      </div>
      {error && <p className="text-xs text-[#ff9a92]">{error.message}</p>}
    </form>
  )
}
