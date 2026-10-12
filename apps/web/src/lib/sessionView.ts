import type { SessionView } from '../api/events'

/** A complete SessionView with neutral defaults, for the demo and tests. */
export const sessionView = (name: string, over: Partial<SessionView> = {}): SessionView => ({
  name,
  kind: 'geral',
  label: 'Geral',
  model: 'sonnet',
  effort: null,
  cwd: '~',
  project: null,
  workspace: null,
  branch: null,
  status: 'idle',
  phase: null,
  task: null,
  activity: null,
  queue: 0,
  waiting: false,
  connected: false,
  tasks_done: 0,
  tokens: 0,
  last_summary: null,
  protected: false,
  subagents: [],
  ...over,
})
