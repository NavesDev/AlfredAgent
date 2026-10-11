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
    <aside className="flex h-full flex-col border-white/10 bg-[#0a0d16]/95 backdrop-blur md:border-l">
      <header className="flex items-center justify-between border-b border-white/10 px-5 py-3">
        <h2 className="text-sm font-medium tracking-wide">Transcrição</h2>
        <div className="flex gap-2">
          <button
            onClick={copy}
            disabled={turns.length === 0}
            className="rounded-md px-2.5 py-1 text-xs text-gray-300 hover:bg-white/10 disabled:opacity-40"
          >
            {copied ? 'Copiado' : 'Copiar'}
          </button>
          <button
            onClick={onClose}
            aria-label="Fechar transcrição"
            className="rounded-md px-2 py-1 text-xs text-gray-400 hover:bg-white/10"
          >
            ✕
          </button>
        </div>
      </header>
      <div ref={list} className="flex-1 overflow-y-auto">
        {turns.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-gray-500">
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
