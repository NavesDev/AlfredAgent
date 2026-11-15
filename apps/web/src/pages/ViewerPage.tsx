import { useEffect } from 'react'
import { useSearchParams } from 'react-router'
import { Loading } from '../features/results/components/ResultBody'
import { ResultViewer } from '../features/results/components/ResultViewer'
import { usePresentation } from '../features/results/hooks/usePresentation'
import { useResultActions } from '../features/results/hooks/useResultActions'
import { useResult } from '../features/results/hooks/useResults'
import { isLocalHost } from '../features/results/lib/results'
import { useEvents } from '../hooks/useEvents'
import { appWindow, isDesktop } from '../lib/desktop'

/** Closes the viewer: the `viewer` window on the desktop, the tab elsewhere. */
const closeWindow = () => (isDesktop() ? void appWindow().close() : window.close())

/** The expanded mode, at `/viewer?id=<result>&i=<slide>` (its own window on the desktop). An
 * unknown result closes it; Esc, ✕ or "pode fechar" close it too. */
export function ViewerPage() {
  const [params, setParams] = useSearchParams()
  const id = Number(params.get('id'))
  const index = Number(params.get('i') ?? 0) || 0
  const result = useResult(id)
  const presentation = usePresentation()
  const { open } = useResultActions()
  const invalid = !Number.isInteger(id) || id <= 0 || result.isError

  useEffect(() => {
    document.documentElement.classList.add('viewer')
    return () => document.documentElement.classList.remove('viewer')
  }, [])

  useEffect(() => {
    if (invalid) closeWindow()
  }, [invalid])

  useEvents((event) => event.type === 'presentation_closed' && closeWindow())

  if (!result.data) return <Loading />
  return (
    <div className="h-full p-2">
      <ResultViewer
        result={result.data}
        index={index}
        local={isLocalHost(location.hostname)}
        onIndex={(i) => setParams({ id: String(id), i: String(i) }, { replace: true })}
        onOpen={(file, reveal) => open.mutate({ id, index: file, reveal })}
        onClose={() => (presentation.close(), closeWindow())}
      />
    </div>
  )
}
