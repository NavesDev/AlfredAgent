import { useState, type ReactNode } from 'react'
import type { SettingsView } from '../../../api/events'
import { Row, Section, Segmented, Switch } from '../../../components/controls'
import { Gauge, GitBranch, LayoutGrid, Plug, Sparkle, Terminal } from '../../../components/icons'
import { button, PageShell, primaryButton } from '../../../components/layout/PageShell'
import { ModelSelect } from '../../../components/ModelSelect'
import { EFFORTS, field } from '../../../lib/sessionForm'
import { UsageSection } from '../components/UsageSection'
import { useSettings } from '../hooks/useSettings'

const KINDS: Record<string, { label: string; hint: string; icon: ReactNode }> = {
  alfred: { label: 'Alfred', hint: 'Agente principal, responde por voz', icon: <Sparkle /> },
  geral: { label: 'Geral', hint: 'Sessões sem ambiente', icon: <Terminal /> },
  implementacao: { label: 'Implementação', hint: 'Sessões que editam código', icon: <GitBranch /> },
}

const FIGURE_SCALES = [1, 1.25, 1.5, 1.75, 2] // the server accepts the same values

export function SettingsPage() {
  const { settings, save } = useSettings()
  return (
    <PageShell title="Configurações" subtitle="Uso, modelos, limites e MCPs das sessões do Alfred.">
      <UsageSection />
      {settings ? <Form key={JSON.stringify(settings)} settings={settings} save={save} /> : null}
    </PageShell>
  )
}

function Form({
  settings,
  save,
}: {
  settings: SettingsView
  save: ReturnType<typeof useSettings>['save']
}) {
  const [draft, setDraft] = useState(settings)
  const [mcp, setMcp] = useState('')
  const set = <K extends keyof SettingsView>(key: K, value: SettingsView[K]) =>
    setDraft((d) => ({ ...d, [key]: value }))
  const setAgent = (kind: string, change: { model?: string; effort?: string | null }) =>
    set(
      'agents',
      draft.agents.map((a) => (a.kind === kind ? { ...a, ...change } : a)),
    )
  const toggleMcp = (name: string) =>
    set(
      'mcp_disabled',
      draft.mcp_disabled.includes(name)
        ? draft.mcp_disabled.filter((n) => n !== name)
        : [...draft.mcp_disabled, name],
    )
  const servers = [...new Set([...settings.known_mcp_servers, ...draft.mcp_disabled])].sort()
  const allMcpOn = draft.mcp_disabled.length === 0
  const { known_mcp_servers: _, ...body } = draft
  const dirty = JSON.stringify(draft) !== JSON.stringify(settings)

  return (
    <>
      <Section
        title="Modelos por tipo de agente"
        description="Vale na próxima conexão de cada sessão. Uma sessão pode sobrescrever no painel dela."
      >
        {draft.agents.map((a) => {
          const kind = KINDS[a.kind] ?? { label: a.kind, hint: '', icon: <Terminal /> }
          return (
            <Row key={a.kind} title={kind.label} description={kind.hint} icon={kind.icon}>
              <div className="flex flex-wrap items-center gap-2">
                <div className="w-44">
                  <ModelSelect
                    label={`Modelo ${kind.label}`}
                    value={a.model}
                    onChange={(model) => setAgent(a.kind, { model })}
                  />
                </div>
                <Segmented
                  label={`Effort ${kind.label}`}
                  value={a.effort ?? ''}
                  onChange={(effort) => setAgent(a.kind, { effort: effort || null })}
                  options={[
                    { value: '', label: 'padrão' },
                    ...EFFORTS.map((e) => ({ value: e, label: e })),
                  ]}
                />
              </div>
            </Row>
          )
        })}
      </Section>

      <Section title="Limites" description="Quantos processos claude ficam vivos e quando dormem.">
        <Row
          title="Sessões abertas ao mesmo tempo"
          description="As demais esperam vaga."
          icon={<Gauge />}
        >
          <Stepper
            label="Sessões abertas ao mesmo tempo"
            value={draft.max_active_sessions}
            onChange={(v) => set('max_active_sessions', v)}
          />
        </Row>
        <Row
          title="Minutos ociosos até dormir"
          description="Retoma a conversa na próxima tarefa."
          icon={<Gauge />}
        >
          <Stepper
            label="Minutos ociosos até dormir"
            value={draft.idle_minutes}
            onChange={(v) => set('idle_minutes', v)}
            unit="min"
          />
        </Row>
      </Section>

      <Section title="Painel" description="Como o mapa de sessões aparece.">
        <Row
          title="Tamanho dos agentes no mapa"
          description="1× é o tamanho original."
          icon={<LayoutGrid />}
        >
          <Segmented
            label="Tamanho dos agentes no mapa"
            value={String(draft.figure_scale)}
            onChange={(v) => set('figure_scale', Number(v))}
            options={FIGURE_SCALES.map((n) => ({
              value: String(n),
              label: `${String(n).replace('.', ',')}×`,
            }))}
          />
        </Row>
      </Section>

      <Section
        title="MCPs nas sessões de implementação"
        description="Todos ligados por padrão. Desligue os que essas sessões não devem carregar."
      >
        {servers.length > 1 && (
          <Row title="Todos os MCPs" icon={<Plug />}>
            <button
              type="button"
              onClick={() => set('mcp_disabled', allMcpOn ? servers : [])}
              className={button}
            >
              {allMcpOn ? 'Desligar todos' : 'Ligar todos'}
            </button>
          </Row>
        )}
        {servers.map((name) => (
          <Row
            key={name}
            title={<span className="font-mono text-[13px]">{name}</span>}
            icon={<Plug />}
          >
            <Switch
              label={`MCP ${name}`}
              checked={!draft.mcp_disabled.includes(name)}
              onChange={() => toggleMcp(name)}
            />
          </Row>
        ))}
        {servers.length === 0 && (
          <p className="px-4 py-3.5 text-xs text-gray-500">
            Os nomes aparecem aqui depois que uma sessão de implementação conectar.
          </p>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (mcp.trim() && !draft.mcp_disabled.includes(mcp.trim())) toggleMcp(mcp.trim())
            setMcp('')
          }}
          className="flex gap-2 px-4 py-3"
        >
          <input
            aria-label="Desligar MCP"
            placeholder="desligar outro pelo nome"
            value={mcp}
            onChange={(e) => setMcp(e.target.value)}
            className={`${field} min-w-0 flex-1 font-mono`}
          />
          <button className={button} disabled={!mcp.trim()}>
            Desligar
          </button>
        </form>
      </Section>

      <div
        className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition ${dirty ? 'sticky bottom-4 z-10 border-white/15 bg-[#111113] shadow-[0_-8px_40px_rgba(9,9,11,0.9)]' : 'border-transparent'}`}
      >
        <p className="flex-1 text-xs text-gray-400">
          {save.error ? (
            <span className="text-red-300">{save.error.message}</span>
          ) : dirty ? (
            'Alterações não salvas'
          ) : save.isSuccess ? (
            'Salvo.'
          ) : null}
        </p>
        {dirty && (
          <button onClick={() => setDraft(settings)} className={button}>
            Descartar
          </button>
        )}
        <button
          onClick={() => save.mutate(body)}
          disabled={!dirty || save.isPending}
          className={primaryButton}
        >
          {save.isPending ? 'Salvando…' : 'Salvar'}
        </button>
      </div>
    </>
  )
}

function Stepper({
  value,
  onChange,
  label,
  unit,
}: {
  value: number
  onChange: (value: number) => void
  label: string
  unit?: string
}) {
  const step =
    'grid size-7 place-items-center text-gray-400 hover:text-gray-100 disabled:opacity-30'
  return (
    <div className="inline-flex items-center rounded-lg border border-white/10 bg-black/30">
      <button
        type="button"
        aria-label="Diminuir"
        className={step}
        disabled={value <= 1}
        onClick={() => onChange(value - 1)}
      >
        −
      </button>
      <input
        type="number"
        min={1}
        aria-label={label}
        value={value}
        onChange={(e) => onChange(Math.max(1, Number(e.target.value)))}
        className="w-10 [appearance:textfield] bg-transparent text-center text-sm text-gray-100 outline-none [&::-webkit-inner-spin-button]:appearance-none"
      />
      {unit && <span className="pr-1 text-xs text-gray-500">{unit}</span>}
      <button
        type="button"
        aria-label="Aumentar"
        className={step}
        onClick={() => onChange(value + 1)}
      >
        +
      </button>
    </div>
  )
}
