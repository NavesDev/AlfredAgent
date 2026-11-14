import { useState, type FormEvent } from 'react'
import type { Project } from '../api/events'
import { EFFORTS, field, KINDS, type NewSession } from '../lib/sessionForm'
import { ModelSelect } from './ModelSelect'

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
        <select
          aria-label="Tipo"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          className={field}
        >
          {KINDS.map((k) => (
            <option key={k.kind} value={k.kind}>
              {k.label}
            </option>
          ))}
        </select>
        <input
          aria-label="Nome"
          placeholder="nome (ex: back)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={`${field} min-w-0 flex-1`}
          autoFocus
        />
      </div>
      <select
        aria-label="Ambiente"
        value={workspace ?? ''}
        onChange={(e) => setWorkspace(e.target.value ? Number(e.target.value) : null)}
        className={field}
      >
        {!needsWorkspace && <option value="">sem ambiente (home)</option>}
        {scoped.map((p) => (
          <optgroup key={p.id} label={p.name}>
            {p.workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
                {w.branch ? ` · ⎇ ${w.branch}` : ''}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <div className="flex gap-2">
        <div className="min-w-0 flex-1">
          <ModelSelect
            label="Modelo"
            placeholder="modelo padrão do tipo"
            value={model}
            onChange={setModel}
          />
        </div>
        <select
          aria-label="Effort"
          value={effort}
          onChange={(e) => setEffort(e.target.value)}
          className={field}
        >
          <option value="">effort padrão</option>
          {EFFORTS.map((e) => (
            <option key={e}>{e}</option>
          ))}
        </select>
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
