import { Row, Section } from '../../../components/controls'
import { Gauge, Sparkle } from '../../../components/icons'
import { formatTokens } from '../../../lib/format'
import { useNow, useUsage } from '../hooks/useUsage'
import {
  percentOf,
  readAgo,
  resetsIn,
  sortLimits,
  TONE_TEXT,
  toneOf,
  windowLabel,
} from '../lib/usage'
import { UsageBar } from './UsageBar'

const STATUS = { allowed: '', allowed_warning: 'perto do limite', rejected: 'bloqueado' }

/** Everything about usage: the plan's windows, the session slots and what each session spent. */
export function UsageSection() {
  const usage = useUsage()
  const now = useNow()
  if (!usage) return null
  const limits = sortLimits(usage.limits)
  const spenders = [...usage.sessions].sort((a, b) => b.tokens - a.tokens)

  return (
    <div id="uso" className="flex scroll-mt-20 flex-col gap-6">
      <Section
        title="Uso e limites do Claude"
        description="O Claude informa os limites enquanto o Alfred ou uma sessão trabalha; o valor é o da última leitura."
      >
        {limits.map((limit) => {
          const percent = percentOf(limit)
          const tone = toneOf(limit)
          const notes = [
            STATUS[limit.status],
            resetsIn(limit.resets_at, now),
            readAgo(limit.read_at, now),
          ]
          return (
            <Row
              key={limit.window}
              title={windowLabel(limit.window)}
              description={notes.filter(Boolean).join(' · ')}
              icon={<Gauge />}
            >
              <div className="flex w-48 items-center gap-2">
                <UsageBar percent={percent} tone={tone} />
                <span className={`w-10 text-right text-xs tabular-nums ${TONE_TEXT[tone]}`}>
                  {percent == null ? '—' : `${percent}%`}
                </span>
              </div>
            </Row>
          )
        })}
        {limits.length === 0 && (
          <p className="px-4 py-3.5 text-xs text-gray-500">
            Ainda sem leitura desde que o servidor iniciou. Aparece depois da próxima tarefa.
          </p>
        )}
      </Section>

      <Section title="Sessões" description="Processos claude abertos e o gasto de cada sessão.">
        <Row
          title="Vagas em uso"
          description={`Tempo máximo por tarefa: ${Math.round(usage.task_timeout_s / 60)} min`}
          icon={<Sparkle />}
        >
          <span className="text-xs text-gray-300 tabular-nums">
            {usage.open_sessions} de {usage.max_active_sessions}
          </span>
        </Row>
        {spenders.map((s) => {
          const share = s.context_max
            ? Math.round(((s.context_tokens ?? 0) / s.context_max) * 100)
            : null
          return (
            <Row
              key={s.name}
              title={s.name}
              description={
                share == null
                  ? 'contexto ainda não medido'
                  : `contexto ${formatTokens(s.context_tokens ?? 0)} de ${formatTokens(s.context_max!)} (${share}%)`
              }
            >
              <span className="text-xs text-gray-400 tabular-nums">
                {formatTokens(s.tokens)} tokens
              </span>
            </Row>
          )
        })}
      </Section>
    </div>
  )
}
