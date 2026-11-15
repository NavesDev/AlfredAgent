import { Row, Section } from '../../../components/controls'
import { Download, RotateCcw } from '../../../components/icons'
import { button, primaryButton } from '../../../components/layout/PageShell'
import { useUpdate } from '../hooks/useUpdate'
import { useNow } from '../hooks/useUsage'
import { noteBlocks } from '../lib/notes'
import { span } from '../lib/usage'

/** Current version, the newest release with its notes, and the button that updates (ADR 0013). */
export function UpdateSection() {
  const { update, check, apply } = useUpdate()
  const now = useNow()
  if (!update) return null
  const updating = update.status === 'updating' || apply.isPending
  const checked = update.checked_at
    ? `verificado há ${span(now / 1000 - update.checked_at)}`
    : 'ainda não verificado'
  const error = apply.error?.message ?? (update.status === 'error' ? update.error : null)

  return (
    <div className="flex flex-col gap-6">
      <Section title="Versão">
        <Row
          icon={<Download className="size-[15px]" />}
          title={
            update.available
              ? `Nova versão ${update.latest}`
              : `Alfred ${update.current ?? 'sem versão'}`
          }
          description={
            updating
              ? 'Atualizando; o Alfred vai reiniciar e volta sozinho.'
              : update.available
                ? `Você está na ${update.current ?? 'versão sem tag'} · ${checked}`
                : `Está atualizado · ${checked}`
          }
        >
          {update.available ? (
            <button
              type="button"
              disabled={updating}
              onClick={() => apply.mutate()}
              className={`${primaryButton} disabled:opacity-50`}
            >
              {updating ? 'Atualizando…' : `Atualizar para ${update.latest}`}
            </button>
          ) : (
            <button
              type="button"
              disabled={check.isPending || update.status === 'checking'}
              onClick={() => check.mutate()}
              className={`${button} inline-flex items-center gap-1.5 disabled:opacity-50`}
            >
              <RotateCcw
                className={`size-3.5 ${check.isPending || update.status === 'checking' ? 'animate-spin-slow' : ''}`}
              />
              Procurar atualizações
            </button>
          )}
        </Row>
        {error && <p className="px-4 py-3 text-xs text-[#ff9a92]">{error}</p>}
      </Section>

      {update.available && update.notes && (
        <Section title={`Novidades da ${update.latest}`}>
          <div className="flex flex-col gap-1.5 px-4 py-3 text-sm">
            {noteBlocks(update.notes).map((block, i) =>
              block.kind === 'heading' ? (
                <h4 key={i} className="mt-2 text-xs font-semibold text-ink-2 first:mt-0">
                  {block.text}
                </h4>
              ) : (
                <p key={i} className={block.kind === 'item' ? 'flex gap-2' : 'text-ink-2'}>
                  {block.kind === 'item' && <span className="text-ink-3">•</span>}
                  <span>{block.text}</span>
                </p>
              ),
            )}
          </div>
        </Section>
      )}

      {update.last && (
        <Section title="Última atualização">
          <Row
            title={`${update.last.previous ?? '?'} → ${update.last.to}`}
            description={
              update.last.ok
                ? `Concluída há ${span(now / 1000 - update.last.at)}`
                : (update.last.error ?? 'Falhou')
            }
          >
            <span
              className={`size-2 rounded-full ${update.last.ok ? 'bg-apple-green' : 'bg-apple-red'}`}
            />
          </Row>
        </Section>
      )}
    </div>
  )
}
