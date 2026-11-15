import { useEffect, useState, type ReactNode } from 'react'
import type { SettingsView } from '../../../api/events'
import { Row, Section, Segmented, Switch } from '../../../components/controls'
import { Gauge, GitBranch, Image, Plug, Sparkle, Terminal } from '../../../components/icons'
import { button, PageShell, primaryButton } from '../../../components/layout/PageShell'
import { ModelSelect } from '../../../components/ModelSelect'
import { Picker } from '../../../components/Picker'
import { EFFORTS, field } from '../../../lib/sessionForm'
import { SettingsNav } from '../components/SettingsNav'
import { UsageSection } from '../components/UsageSection'
import { SECTIONS, sectionFromHash, type SectionId } from '../lib/sections'
import { useSettings } from '../hooks/useSettings'

const KINDS: Record<string, { label: string; hint: string; icon: ReactNode }> = {
  alfred: { label: 'Alfred', hint: 'Agente principal, responde por voz', icon: <Sparkle /> },
  geral: { label: 'Geral', hint: 'Sessões sem ambiente', icon: <Terminal /> },
  implementacao: { label: 'Implementação', hint: 'Sessões que editam código', icon: <GitBranch /> },
}

export function SettingsPage() {
  const { settings, save } = useSettings()
  const [section, setSection] = useState<SectionId>(() => sectionFromHash(window.location.hash))
  useEffect(() => {
    const onHash = () => setSection(sectionFromHash(window.location.hash))
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  const title = SECTIONS.find((s) => s.id === section)?.label

  return (
    <PageShell
      title={title}
      aside={
        <>
          <h2 className="px-1.5 text-2xl font-bold tracking-tight">Configurações</h2>
          <SettingsNav current={section} onSelect={setSection} />
        </>
      }
    >
      {section === 'uso' ? (
        <UsageSection />
      ) : settings ? (
        <Form key={JSON.stringify(settings)} settings={settings} save={save} section={section} />
      ) : null}
    </PageShell>
  )
}

export function Form({
  settings,
  save,
  section,
}: {
  settings: SettingsView
  save: ReturnType<typeof useSettings>['save']
  section: SectionId
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
  const { known_mcp_servers: _, image_mcp_servers: generators, image_mcp, ...rest } = draft
  const body = { ...rest, image_mcp: image_mcp ?? '' } // '' goes back to automatic
  const dirty = JSON.stringify(draft) !== JSON.stringify(settings)

  return (
    <>
      {section === 'modelos' && (
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
        </>
      )}
      {section === 'sessoes' && (
        <>
          <Section
            title="Limites"
            description="Quantos processos claude ficam vivos e quando dormem."
          >
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
          <Section
            title="Features"
            description="Orienta o Alfred em ambientes sem modo próprio; ele decide caso a caso."
          >
            <Row title="Feature nova" icon={<GitBranch />}>
              <Segmented
                label="Feature nova, por padrão"
                value={draft.implementation_mode}
                onChange={(mode) =>
                  set('implementation_mode', mode as SettingsView['implementation_mode'])
                }
                options={[
                  { value: 'worktree', label: 'Worktree novo' },
                  { value: 'ambiente', label: 'No próprio ambiente' },
                ]}
              />
            </Row>
          </Section>
        </>
      )}
      {section === 'mcps' && (
        <>
          <Section
            title="Gerador de imagens"
            description="Desenha o retrato de cada sessão. No automático, o Alfred escolhe entre os MCPs e guarda o que funcionou."
          >
            <Row title="MCP favorito" icon={<Image />}>
              <div className="w-48">
                <Picker
                  label="Gerador de imagens"
                  mono
                  value={draft.image_mcp ?? ''}
                  onChange={(name) => set('image_mcp', name || null)}
                  options={[
                    { id: '', label: 'Automático', hint: 'escolhe e guarda o que funcionar' },
                    ...[...new Set([...generators, ...(draft.image_mcp ? [draft.image_mcp] : [])])]
                      .sort()
                      .map((name) => ({ id: name, label: name })),
                  ]}
                />
              </div>
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
              <p className="px-4 py-3.5 text-xs text-ink-3">
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
        </>
      )}

      <div
        className={`flex items-center gap-3 rounded-full px-4 py-2.5 transition ${dirty ? 'glass sticky bottom-4 z-10' : ''}`}
      >
        <p className="flex-1 text-xs text-ink-2">
          {save.error ? (
            <span className="text-[#ff9a92]">{save.error.message}</span>
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
  const step = 'grid size-7 place-items-center text-ink-2 hover:text-ink disabled:opacity-30'
  return (
    <div className="inline-flex items-center gap-1 rounded-[10px] bg-fill">
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
        className="w-10 [appearance:textfield] bg-transparent text-center text-sm text-ink outline-none [&::-webkit-inner-spin-button]:appearance-none"
      />
      {unit && <span className="pr-1 text-xs text-ink-3">{unit}</span>}
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
