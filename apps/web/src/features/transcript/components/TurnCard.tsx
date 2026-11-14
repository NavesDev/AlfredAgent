import { describe, speaker } from '../lib/turns'
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
      <span className="text-ink-2 tabular-nums">
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
    <article className="space-y-2.5 rounded-[18px] bg-well px-3.5 py-3">
      <header className="flex items-center justify-between text-xs text-ink-3">
        <time>{time(turn.heardAt)}</time>
        {turn.source && (
          <span className="uppercase tracking-wider">
            {turn.source === 'voice' ? 'voz' : 'painel'}
          </span>
        )}
      </header>

      {turn.userText && (
        <p className="rounded-2xl bg-apple-blue/25 px-3 py-2 text-sm text-ink">
          <span className="mr-1.5 text-xs font-medium text-apple-teal">Você</span>
          {turn.userText}
        </p>
      )}

      {tools.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {tools.map((step, i) => (
            <li key={i} className="rounded-full bg-fill px-2 py-0.5 text-[11px] text-ink-2">
              <span title={step.content}>{describe(step.label, step.detail)}</span>
            </li>
          ))}
        </ul>
      )}

      {turn.summary && (
        <p className="text-sm text-ink">
          <span className="mr-1.5 text-xs font-medium text-apple-green">
            {speaker(turn.session)}
          </span>
          {turn.summary}
        </p>
      )}

      {extra && (
        <details className="group text-sm" open={!turn.summary}>
          <summary className="cursor-pointer text-xs text-ink-2 select-none hover:text-ink">
            {turn.summary ? 'Resposta completa (não falada)' : 'Resposta (sem RESUMO)'}
          </summary>
          <p className="mt-2 whitespace-pre-wrap text-ink-2">{extra}</p>
        </details>
      )}

      {turn.error && (
        <p className="rounded-2xl bg-apple-red/12 px-3 py-2 text-sm text-[#ff9a92]">{turn.error}</p>
      )}

      {!turn.reply && !turn.error && (
        <p className="text-xs text-ink-3 italic">aguardando resposta…</p>
      )}

      {turn.userText && (
        <footer className="flex gap-4 text-[11px] text-ink-3">
          <Metric label="STT" value={turn.sttS} />
          <Metric label="1ª fala" value={turn.firstSpeechS} />
          <Metric label="resposta" value={turn.replyS} />
        </footer>
      )}
    </article>
  )
}
