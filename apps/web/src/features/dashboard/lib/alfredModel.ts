export type Family = 'opus' | 'sonnet' | 'haiku'
export const FAMILIES: Family[] = ['opus', 'sonnet', 'haiku']

/** The family of a model id or alias, so the control bar can show Opus / Sonnet / Haiku. */
export function familyOf(model: string): Family | null {
  const id = model.toLowerCase()
  return FAMILIES.find((family) => id.includes(family)) ?? null
}

type Agent = { kind: string; model: string; effort?: string | null }

/** The agents list with Alfred's model swapped, ready to save with the rest of the settings. */
export function withAlfredModel<T extends Agent>(agents: T[], model: string): T[] {
  return agents.map((a) => (a.kind === 'alfred' ? { ...a, model } : a))
}
