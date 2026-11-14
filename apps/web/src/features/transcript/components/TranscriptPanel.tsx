import { useEffect, useRef, useState } from 'react'
import { toMarkdown } from '../lib/turns'
import type { Turn } from '../types'
import { TurnCard } from './TurnCard'

export function TranscriptPanel({ turns, onClose }: { turns: Turn[]; onClose: () => void }) {
  const list = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    list.current?.scrollTo({ top: list.current.scrollHeight, behavior: 'smooth' })
  }, [turns])

  const copy = async () => {
    await navigator.clipboard.writeText(toMarkdown(turns))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <aside
      aria-label="Transcrição"
      className="glass flex h-full min-h-0 flex-col overflow-hidden rounded-panel"
    >
      <header className="flex items-center justify-between px-5 pt-4 pb-2">
        <h2 className="text-[15px] font-semibold">Transcrição</h2>
        <div className="flex gap-2">
          <button
            onClick={copy}
            disabled={turns.length === 0}
            className="rounded-full px-3 py-1 text-xs text-ink-2 hover:bg-fill disabled:opacity-40"
          >
            {copied ? 'Copiado' : 'Copiar'}
          </button>
          <button
            onClick={onClose}
            aria-label="Fechar transcrição"
            className="rounded-full px-2.5 py-1 text-xs text-ink-2 hover:bg-fill"
          >
            ✕
          </button>
        </div>
      </header>
      <div ref={list} className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto px-3 pb-3">
        {turns.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-ink-3">
            Nada ainda. Fale “Alfred” e o que você disser aparece aqui, com o que ele respondeu e os
            tempos.
          </p>
        ) : (
          turns.map((turn) => <TurnCard key={turn.id} turn={turn} />)
        )}
      </div>
    </aside>
  )
}
