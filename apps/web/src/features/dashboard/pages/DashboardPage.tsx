import { useEffect, useState, type ReactNode } from 'react'
import { AppShell } from '../../../components/layout/AppShell'
import { NewSessionForm } from '../../../components/NewSessionForm'
import { ActivityCards } from '../../assistant/components/ActivityCards'
import { Orb } from '../../assistant/components/Orb'
import { useActivity } from '../../assistant/hooks/useActivity'
import { useClearAlfred } from '../../assistant/hooks/useClearAlfred'
import { useVoice } from '../../assistant/hooks/useVoice'
import { ResultCard } from '../../results/components/ResultCard'
import { ResultHistory } from '../../results/components/ResultHistory'
import { usePresentation } from '../../results/hooks/usePresentation'
import { useResultActions } from '../../results/hooks/useResultActions'
import { isLocalHost } from '../../results/lib/results'
import { SessionCard } from '../../sessions/components/SessionCard'
import { SessionList } from '../../sessions/components/SessionList'
import { useProjectList } from '../../sessions/hooks/useProjectList'
import { useSessionActions } from '../../sessions/hooks/useSessionActions'
import { useSessions } from '../../sessions/hooks/useSessions'
import { UpdatePill } from '../../settings/components/UpdatePill'
import { UsagePill } from '../../settings/components/UsagePill'
import { useSettings } from '../../settings/hooks/useSettings'
import { TranscriptPanel } from '../../transcript/components/TranscriptPanel'
import { useTranscript } from '../../transcript/hooks/useTranscript'
import { ControlBar } from '../components/ControlBar'
import { familyOf, withAlfredModel } from '../lib/alfredModel'
import { panelShowsCard } from '../lib/presentation'
import { isDesktop, openViewer } from '../../../lib/desktop'

const STORAGE_KEY = 'alfred.showTranscript'
/** The card leaves on its own after this long without the mouse on it (D13). */
const CARD_MS = 30_000

/** Expanded mode: the `viewer` window on the desktop, a new tab in a browser. */
const expand = (id: number, slide: number) =>
  isDesktop()
    ? void openViewer(id, slide).catch(() => {})
    : void window.open(`/viewer?id=${id}&i=${slide}`, '_blank')

function useStoredToggle(key: string) {
  const [on, setOn] = useState(() => {
    try {
      return localStorage.getItem(key) === '1'
    } catch {
      return false
    }
  })
  useEffect(() => {
    try {
      localStorage.setItem(key, on ? '1' : '0')
    } catch {
      // private mode: the toggle just won't persist
    }
  }, [key, on])
  return [on, setOn] as const
}

/** The main screen, "window" layout: sessions | Alfred | the open session or the transcript. */
export function DashboardPage() {
  const voice = useVoice()
  const activity = useActivity()
  const turns = useTranscript()
  const sessions = useSessions()
  const projects = useProjectList()
  const actions = useSessionActions()
  const { settings, save } = useSettings()
  const clearAlfred = useClearAlfred()
  const presentation = usePresentation()
  const results = useResultActions()
  const local = isLocalHost(location.hostname)
  const shown = presentation.current
  const [showTranscript, setShowTranscript] = useStoredToggle(STORAGE_KEY)
  const [selected, setSelected] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const session = sessions.find((s) => s.name === selected) ?? null
  const alfredModel = settings?.agents.find((a) => a.kind === 'alfred')?.model ?? ''

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement
      if (typing || e.metaKey || e.ctrlKey) return
      if (e.key.toLowerCase() === 't') setShowTranscript((v) => !v)
      if (e.key === 'Escape') {
        setSelected(null)
        setCreating(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setShowTranscript])

  const open = (name: string) => (setCreating(false), setSelected(name))
  const error = actions.clear.error ?? actions.remove.error ?? actions.change.error

  let side: ReactNode = null
  if (creating)
    side = (
      <section
        aria-label="Nova sessão"
        className="glass flex flex-col gap-4 overflow-y-auto rounded-panel p-5"
      >
        <h2 className="text-lg font-semibold">Nova sessão</h2>
        <NewSessionForm
          projects={projects}
          pending={actions.create.isPending}
          error={actions.create.error?.message}
          onSubmit={(body) =>
            actions.create.mutate(body, { onSuccess: (created) => open(created.name) })
          }
          onCancel={() => setCreating(false)}
        />
      </section>
    )
  else if (session)
    side = (
      <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
        <SessionCard
          session={session}
          onClose={() => setSelected(null)}
          onClear={() => actions.clear.mutate(session.name)}
          onDelete={() =>
            actions.remove.mutate(session.name, { onSuccess: () => setSelected(null) })
          }
          onChange={(change) => actions.change.mutate({ name: session.name, ...change })}
          error={error?.message}
        />
        <div className="glass rounded-panel p-4">
          <ResultHistory session={session.name} local={local} />
        </div>
      </div>
    )
  else if (showTranscript)
    side = <TranscriptPanel turns={turns} onClose={() => setShowTranscript(false)} />

  return (
    <AppShell>
      <div
        className={`grid h-full grid-cols-1 gap-4 overflow-y-auto md:gap-6 md:overflow-visible ${
          side
            ? 'md:grid-cols-[minmax(220px,23%)_minmax(0,1fr)_minmax(280px,27%)]'
            : 'md:grid-cols-[minmax(220px,23%)_minmax(0,1fr)]'
        }`}
      >
        <SessionList
          sessions={sessions}
          selected={selected}
          onSelect={(name) => (name === selected ? setSelected(null) : open(name))}
          onNew={() => (setSelected(null), setCreating(true))}
        />

        <section
          aria-label="Alfred"
          className="flex min-h-[420px] min-w-0 flex-col items-center justify-center gap-5"
        >
          <div className="grid min-h-0 w-full shrink place-items-center">
            <Orb state={voice.state} level={voice.level} />
          </div>
          {activity.length > 0 && (
            <div className="relative h-36 w-full shrink-0">
              <ActivityCards items={activity} />
            </div>
          )}
          {turns.at(-1)?.summary && (
            <p className="glass flex max-w-full items-center gap-3 rounded-full py-2 pr-5 pl-2 text-[15px] leading-snug">
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-[radial-gradient(circle_at_35%_30%,#fff,#c9c9d1_40%,#5b5b66)] text-[13px] font-semibold text-[#1c1c1e]">
                A
              </span>
              <span className="line-clamp-2">{turns.at(-1)?.summary}</span>
            </p>
          )}
          <ControlBar
            state={voice.state}
            family={familyOf(alfredModel)}
            onFamily={(family) =>
              settings && save.mutate({ agents: withAlfredModel(settings.agents, family) })
            }
            onNewConversation={() => clearAlfred.mutate()}
            clearing={clearAlfred.isPending}
            transcript={showTranscript && !session && !creating}
            onTranscript={() => (
              setSelected(null),
              setCreating(false),
              setShowTranscript((v) => !v)
            )}
          >
            <UpdatePill />
            <UsagePill />
          </ControlBar>
        </section>

        {side && <div className="flex max-h-full min-h-0 flex-col self-center">{side}</div>}
      </div>
      {shown && panelShowsCard(shown.mode, isDesktop()) && (
        <div className="fixed top-14 right-4 z-30 animate-pill-in">
          <ResultCard
            key={shown.result.id}
            result={shown.result}
            local={local}
            onExpand={(slide) => expand(shown.result.id, slide)}
            onOpen={(index, reveal) => results.open.mutate({ id: shown.result.id, index, reveal })}
            onClose={presentation.close}
            autoCloseMs={CARD_MS}
            onDismiss={presentation.dismiss}
          />
        </div>
      )}
    </AppShell>
  )
}
