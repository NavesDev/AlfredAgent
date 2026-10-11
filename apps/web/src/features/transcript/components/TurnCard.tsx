import type { Turn } from '../types'

const time = (ts: number) =>
  new Date(ts * 1000).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <span title={label}>
      {label}{' '}
      <span className="text-gray-300 tabular-nums">
        {value === null ? '–' : `${value.toFixed(2)}s`}
      </span>
    </span>
  )
}

export function TurnCard({ turn }: { turn: Turn }) {
  const tools = turn.steps.filter((s) => s.kind === 'tool')
  const extra =
    turn.reply && turn.summary ? turn.reply.replace(/^RESUMO:.*\n*/, '').trim() : turn.reply
  return (
    <article className="space-y-3 border-b border-white/5 px-5 py-4">
      <header className="flex items-center justify-between text-xs text-gray-500">
        <time>{time(turn.heardAt)}</time>
        {turn.source && (
          <span className="uppercase tracking-wider">
            {turn.source === 'voice' ? 'voz' : 'painel'}
          </span>
        )}
      </header>

      {turn.userText && (
        <p className="rounded-lg bg-white/5 px-3 py-2 text-sm text-gray-100">
          <span className="mr-1.5 text-xs font-medium text-teal-300">Você</span>
          {turn.userText}
        </p>
      )}

      {tools.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {tools.map((step, i) => (
            <li
              key={i}
              className="rounded border border-amber-400/20 bg-amber-400/5 px-1.5 py-0.5 font-mono text-[11px] text-amber-200/80"
            >
              {step.content}
            </li>
          ))}
        </ul>
      )}

      {turn.summary && (
        <p className="text-sm text-gray-100">
          <span className="mr-1.5 text-xs font-medium text-emerald-300">Alfred</span>
          {turn.summary}
        </p>
      )}

      {extra && (
        <details className="group text-sm" open={!turn.summary}>
          <summary className="cursor-pointer text-xs text-gray-400 select-none hover:text-gray-200">
            {turn.summary ? 'Resposta completa (não falada)' : 'Resposta (sem RESUMO)'}
          </summary>
          <p className="mt-2 whitespace-pre-wrap text-gray-300">{extra}</p>
        </details>
      )}

      {turn.error && (
        <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">{turn.error}</p>
      )}

      {!turn.reply && !turn.error && (
        <p className="text-xs text-gray-500 italic">aguardando resposta…</p>
      )}

      {turn.userText && (
        <footer className="flex gap-4 text-[11px] text-gray-500">
          <Metric label="STT" value={turn.sttS} />
          <Metric label="1ª fala" value={turn.firstSpeechS} />
          <Metric label="resposta" value={turn.replyS} />
        </footer>
      )}
    </article>
  )
}
