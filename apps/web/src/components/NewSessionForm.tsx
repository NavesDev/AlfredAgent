import { useState, type FormEvent } from 'react'
import type { Project } from '../api/events'
import { EFFORT_OPTIONS, field, KINDS, type NewSession } from '../lib/sessionForm'
import { ModelSelect } from './ModelSelect'
import { Picker } from './Picker'

// Used by the projects pages and by the project hub on the dashboard. It only renders and
// reports; each feature passes its own data and mutation.

type Props = {
  projects: Project[]
  projectId?: number
  pending?: boolean
  error?: string | null
  onSubmit: (session: NewSession) => void
  onCancel?: () => void
}

export function NewSessionForm({ projects, projectId, pending, error, onSubmit, onCancel }: Props) {
  const scoped = projectId === undefined ? projects : projects.filter((p) => p.id === projectId)
  const firstWorkspace = scoped.flatMap((p) => p.workspaces)[0]?.id ?? null
  const [kind, setKind] = useState('implementacao')
  const [name, setName] = useState('')
  const [workspace, setWorkspace] = useState<number | null>(firstWorkspace)
  const [model, setModel] = useState('')
  const [effort, setEffort] = useState('')
  const needsWorkspace = KINDS.find((k) => k.kind === kind)?.needsWorkspace ?? false

  const submit = (e: FormEvent) => {
    e.preventDefault()
    onSubmit({
      kind,
      name: name.trim(),
      workspace_id: workspace,
      model: model.trim() || null,
      effort: effort || null,
    })
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2 text-sm">
      <div className="flex gap-2">
        <div className="w-40 shrink-0">
          <Picker
            label="Tipo"
            value={kind}
            onChange={setKind}
            options={KINDS.map((k) => ({ id: k.kind, label: k.label }))}
          />
        </div>
        <input
          aria-label="Nome"
          placeholder="nome (ex: back)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={`${field} min-w-0 flex-1`}
          autoFocus
        />
      </div>
      <Picker
        label="Ambiente"
        value={workspace == null ? '' : String(workspace)}
        onChange={(id) => setWorkspace(id ? Number(id) : null)}
        options={[
          ...(needsWorkspace ? [] : [{ id: '', label: 'sem ambiente (home)' }]),
          ...scoped.flatMap((p) =>
            p.workspaces.map((w) => ({
              id: String(w.id),
              label: w.name,
              hint: w.branch ? `⎇ ${w.branch}` : undefined,
              group: p.name,
            })),
          ),
        ]}
      />
      <div className="flex gap-2">
        <div className="min-w-0 flex-1">
          <ModelSelect
            label="Modelo"
            placeholder="modelo padrão do tipo"
            value={model}
            onChange={setModel}
          />
        </div>
        <div className="w-36 shrink-0">
          <Picker
            label="Effort"
            value={effort}
            onChange={setEffort}
            options={[{ id: '', label: 'effort padrão' }, ...EFFORT_OPTIONS.slice(1)]}
          />
        </div>
      </div>
      {error && <p className="text-xs text-[#ff9a92]">{error}</p>}
      <div className="flex justify-end gap-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md px-3 py-1.5 text-xs text-ink-2 hover:text-ink"
          >
            Cancelar
          </button>
        )}
        <button
          type="submit"
          disabled={pending || !name.trim() || (needsWorkspace && workspace === null)}
          className="rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-[#111] hover:bg-white disabled:opacity-40"
        >
          Criar sessão
        </button>
      </div>
    </form>
  )
}
