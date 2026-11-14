import type { AlfredEvent, Project } from '../../../api/events'

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
