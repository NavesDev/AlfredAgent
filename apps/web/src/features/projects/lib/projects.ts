import type { AlfredEvent, Project, Workspace } from '../../../api/events'

/** Applies a project_* event from the /ws to the cached list. */
export function applyProjectEvent(list: Project[], event: AlfredEvent): Project[] {
  switch (event.type) {
    case 'project_created':
    case 'project_updated': {
      const { project } = event
      const i = list.findIndex((p) => p.id === project.id)
      return i < 0 ? [...list, project] : list.with(i, project)
    }
    case 'project_deleted':
      return list.filter((p) => p.id !== event.id)
    default:
      return list
  }
}

/** "1 ambiente", "3 sessões". */
export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

/** Workspaces in tree order: each one followed by the worktrees made from it, deepest last. */
export function byParent(list: Workspace[]): (Workspace & { depth: number })[] {
  const ids = new Set(list.map((w) => w.id))
  const children = (id: number | null) =>
    list.filter((w) => (id === null ? !w.parent_id || !ids.has(w.parent_id) : w.parent_id === id))
  const walk = (id: number | null, depth: number): (Workspace & { depth: number })[] =>
    children(id).flatMap((w) => [{ ...w, depth }, ...walk(w.id, depth + 1)])
  return walk(null, 0)
}

export type Mode = 'worktree' | 'ambiente'

export const MODE_LABEL: Record<Mode, string> = {
  worktree: 'Worktree novo',
  ambiente: 'No próprio ambiente',
}

/** Picker options for a workspace's mode; '' follows the global setting. */
export const modeOptions = (global: Mode) => [
  { id: '', label: `Global (${MODE_LABEL[global].toLowerCase()})` },
  { id: 'worktree', label: MODE_LABEL.worktree },
  { id: 'ambiente', label: MODE_LABEL.ambiente },
]
