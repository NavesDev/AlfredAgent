// Shared by the new-session form and the session/settings editors.

export type NewSession = {
  kind: string
  name: string
  workspace_id: number | null
  model: string | null
  effort: string | null
}

export const KINDS = [
  { kind: 'implementacao', label: 'Implementação', needsWorkspace: true },
  { kind: 'geral', label: 'Geral', needsWorkspace: false },
]
export const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']

export const field =
  'rounded-xl bg-well px-3 py-2 text-sm text-ink outline-none placeholder:text-ink-3 focus:ring-2 focus:ring-apple-blue/60'

/** Values passed to `claude --model`: the CLI aliases track the newest release of each family. */
export const MODELS = [
  { id: 'opus', label: 'Opus', hint: 'mais recente · trabalho complexo', group: 'Apelidos' },
  { id: 'sonnet', label: 'Sonnet', hint: 'mais recente · equilibrado', group: 'Apelidos' },
  { id: 'haiku', label: 'Haiku', hint: 'mais recente · rápido e barato', group: 'Apelidos' },
  {
    id: 'claude-fable-5-1',
    label: 'Fable 5.1',
    hint: 'tarefas mais difíceis',
    group: 'Versões fixas',
  },
  {
    id: 'claude-opus-5-5',
    label: 'Opus 5.5',
    hint: 'complexo e dia a dia',
    group: 'Versões fixas',
  },
  { id: 'claude-sonnet-5-5', label: 'Sonnet 5.5', hint: 'eficiente', group: 'Versões fixas' },
  { id: 'claude-haiku-5-5', label: 'Haiku 5.5', hint: 'respostas rápidas', group: 'Versões fixas' },
]
