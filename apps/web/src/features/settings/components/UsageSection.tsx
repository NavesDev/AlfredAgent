import { Section } from '../../../components/controls'
import { formatTokens } from '../../../lib/format'
import { gradientFor, initials } from '../../../lib/presence'
import { useNow, useUsage } from '../hooks/useUsage'
import { percentOf, readAgo, resetsIn, sortLimits, toneOf, windowLabel } from '../lib/usage'
import { UsageRing } from './UsageRing'

const STATUS = { allowed: '', allowed_warning: 'perto do limite', rejected: 'bloqueado' }

/** The plan's windows as rings, the open slots and what each session spent. */
export function UsageSection() {
  const usage = useUsage()
  const now = useNow()
  if (!usage) return null
  const limits = sortLimits(usage.limits)
  const spenders = [...usage.sessions].sort((a, b) => b.tokens - a.tokens)
  const most = Math.max(1, ...spenders.map((s) => s.tokens))

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2.5">
        <h3 className="text-[13px] font-semibold tracking-wide text-ink-2 uppercase">
          Plano do Claude
        </h3>
        {limits.length ? (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
            {limits.map((limit) => (
              <UsageRing
                key={limit.window}
                percent={percentOf(limit)}
                tone={toneOf(limit)}
                label={windowLabel(limit.window)}
                note={[
                  STATUS[limit.status],
                  resetsIn(limit.resets_at, now),
                  readAgo(limit.read_at, now),
                ]
                  .filter(Boolean)
                  .join(' · ')}
              />
            ))}
          </div>
        ) : (
          <p className="rounded-[18px] bg-well px-4 py-3.5 text-xs text-ink-3">
            O Claude informa os limites enquanto o Alfred ou uma sessão trabalha. Aparecem depois da
            próxima tarefa.
          </p>
        )}
      </section>

      <Section
        title="Gasto por sessão"
        description={`${usage.open_sessions} de ${usage.max_active_sessions} processos abertos agora.`}
      >
        {spenders.map((s) => {
          const [from, to] = gradientFor(s.name)
          return (
            <div
              key={s.name}
              className="grid grid-cols-[28px_minmax(0,1fr)_minmax(80px,240px)_52px] items-center gap-3 px-4 py-2.5 text-sm"
            >
              <span
                aria-hidden
                style={{ background: `linear-gradient(180deg, ${from}, ${to})` }}
                className="grid size-7 place-items-center rounded-full text-[11px] font-semibold text-white"
              >
                {initials(s.name)}
              </span>
              <span className="truncate">{s.name}</span>
              <span className="h-1.5 overflow-hidden rounded-full bg-fill">
                <span
                  className="block h-full rounded-full bg-[linear-gradient(90deg,#64d2ff,#0a84ff)]"
                  style={{ width: `${(s.tokens / most) * 100}%` }}
                />
              </span>
              <span className="text-right text-xs text-ink-2 tabular-nums">
                {formatTokens(s.tokens)}
              </span>
            </div>
          )
        })}
        {spenders.length === 0 && (
          <p className="px-4 py-3.5 text-xs text-ink-3">Nenhuma sessão ainda.</p>
        )}
      </Section>
    </div>
  )
}
