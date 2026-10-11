import { useEffect, useState } from 'react'
import { useConnection } from '../../../hooks/useEvents'
import { playDemo } from '../../../lib/demo'
import { Assistant } from '../../assistant/components/Assistant'
import { AgentStrip } from '../../sessions/components/AgentStrip'
import { TranscriptPanel } from '../../transcript/components/TranscriptPanel'
import { useTranscript } from '../../transcript/hooks/useTranscript'

const STORAGE_KEY = 'alfred.showTranscript'

const CONNECTION = {
  open: { label: 'conectado', dot: 'bg-emerald-400' },
  connecting: { label: 'conectando', dot: 'bg-amber-400 animate-pulse' },
  closed: { label: 'servidor offline', dot: 'bg-red-400' },
}

function readStored() {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function DashboardPage() {
  const turns = useTranscript()
  const connection = CONNECTION[useConnection()]
  const [showTranscript, setShowTranscript] = useState(readStored)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, showTranscript ? '1' : '0')
    } catch {
      // private mode: the toggle just won't persist
    }
  }, [showTranscript])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (
        e.key.toLowerCase() === 't' &&
        !e.metaKey &&
        !e.ctrlKey &&
        !(e.target instanceof HTMLInputElement)
      )
        setShowTranscript((v) => !v)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const caption = turns.at(-1)?.summary ?? null

  return (
    <div className="flex h-full flex-col bg-[radial-gradient(ellipse_at_center,#0d1424_0%,#05070d_70%)]">
      <header className="flex items-center justify-between px-5 py-4">
        <h1 className="text-base font-semibold tracking-[0.3em] text-gray-200 uppercase">Alfred</h1>
        <div className="flex items-center gap-2">
          <span className="mr-2 flex items-center gap-2 text-xs text-gray-400">
            <span className={`size-1.5 rounded-full ${connection.dot}`} />
            <span className="hidden sm:inline">{connection.label}</span>
          </span>
          <button
            onClick={() => playDemo()}
            title="Simula uma conversa para testar a animação sem o servidor"
            className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-gray-300 hover:bg-white/5"
          >
            Demo
          </button>
          <button
            onClick={() => setShowTranscript((v) => !v)}
            aria-pressed={showTranscript}
            className={`rounded-md border px-3 py-1.5 text-xs ${
              showTranscript
                ? 'border-teal-300/40 bg-teal-300/10 text-teal-200'
                : 'border-white/10 text-gray-300 hover:bg-white/5'
            }`}
          >
            Transcrição <kbd className="ml-1 hidden sm:inline text-[10px] text-gray-500">T</kbd>
          </button>
        </div>
      </header>

      <main className="relative flex min-h-0 flex-1 flex-col md:flex-row">
        <section className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1">
            <Assistant caption={caption} />
          </div>
          <div className="mx-auto w-full max-w-5xl">
            <AgentStrip />
          </div>
        </section>
        {showTranscript && (
          <div className="h-[45%] border-t border-white/10 md:h-auto md:w-[420px] md:border-t-0">
            <TranscriptPanel turns={turns} onClose={() => setShowTranscript(false)} />
          </div>
        )}
      </main>
    </div>
  )
}
