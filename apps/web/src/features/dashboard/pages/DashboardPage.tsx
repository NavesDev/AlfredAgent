import { useEffect, useRef, useState } from 'react'
import { AppHeader } from '../../../components/layout/AppHeader'
import { playDemo } from '../../../lib/demo'
import { Assistant } from '../../assistant/components/Assistant'
import { useClearAlfred } from '../../assistant/hooks/useClearAlfred'
import { Constellation } from '../../sessions/components/Constellation'
import { TranscriptPanel } from '../../transcript/components/TranscriptPanel'
import { useTranscript } from '../../transcript/hooks/useTranscript'

const STORAGE_KEY = 'alfred.showTranscript'

function readStored() {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function DashboardPage() {
  const turns = useTranscript()
  const clearAlfred = useClearAlfred()
  const [showTranscript, setShowTranscript] = useState(readStored)
  const orbRef = useRef<HTMLDivElement>(null)

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
      <AppHeader
        actions={
          <>
            <button
              onClick={() => playDemo()}
              title="Simula uma conversa para testar a animação sem o servidor"
              className="rounded-full border border-white/10 px-3 py-1 text-[11px] text-gray-300 hover:bg-white/5"
            >
              Demo
            </button>
            <button
              onClick={() => clearAlfred.mutate()}
              disabled={clearAlfred.isPending}
              title={
                clearAlfred.isError
                  ? `Não consegui limpar: ${clearAlfred.error.message}`
                  : 'Esquece a conversa de hoje; espera a resposta em andamento terminar'
              }
              className={`rounded-full border px-3 py-1 text-[11px] whitespace-nowrap disabled:opacity-50 ${
                clearAlfred.isError
                  ? 'border-red-400/40 text-red-300'
                  : 'border-white/10 text-gray-300 hover:bg-white/5'
              }`}
            >
              {clearAlfred.isPending ? 'Limpando…' : 'Nova conversa'}
            </button>
            <button
              onClick={() => setShowTranscript((v) => !v)}
              aria-pressed={showTranscript}
              className={`rounded-full border px-3 py-1 text-[11px] ${
                showTranscript
                  ? 'border-teal-300/40 bg-teal-300/10 text-teal-200'
                  : 'border-white/10 text-gray-300 hover:bg-white/5'
              }`}
            >
              Transcrição <kbd className="ml-1 hidden text-[10px] text-gray-500 sm:inline">T</kbd>
            </button>
          </>
        }
      />

      <main className="relative flex min-h-0 flex-1 flex-col md:flex-row">
        <section className="relative min-h-0 flex-1">
          {/* Above the filaments, below the agent nodes */}
          <div className="relative z-10 h-full">
            <Assistant caption={caption} orbRef={orbRef} />
          </div>
          <Constellation anchor={orbRef} />
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
