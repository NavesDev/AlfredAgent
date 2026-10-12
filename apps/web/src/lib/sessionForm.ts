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
  'rounded-md border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-gray-100 outline-none focus:border-white/30'
