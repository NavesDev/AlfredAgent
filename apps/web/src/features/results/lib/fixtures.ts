import type { ResultView } from '../../../api/events'

/** A result as the API sends it, for tests. */
export const resultView = (over: Partial<ResultView> = {}): ResultView => ({
  id: 7,
  session: 'Design',
  source: 'session',
  title: 'Design fez o retrato',
  summary: 'Retrato pronto, estilo 3D.',
  report: null,
  changes: [],
  files: [{ name: 'retrato.png', kind: 'image', size: 5000, exists: true }],
  created_at: 0,
  ...over,
})
