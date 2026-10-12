import { useState } from 'react'
import type { SettingsView } from '../../../api/events'
import { button, card, PageShell } from '../../../components/layout/PageShell'
import { EFFORTS, field } from '../../../lib/sessionForm'
import { useSettings } from '../hooks/useSettings'

const KIND_LABEL: Record<string, string> = {
  alfred: 'Alfred (agente principal)',
  geral: 'Geral',
  implementacao: 'Implementação',
}

export function SettingsPage() {
  const { settings, save } = useSettings()
  return (
    <PageShell title="Configurações">
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
  const { known_mcp_servers: _, ...body } = draft

  return (
    <>
      <section className={card}>
        <h3 className="mb-1 text-sm font-medium text-gray-200">Modelos por tipo de agente</h3>
        <p className="mb-3 text-xs text-gray-500">
          Vale na próxima conexão de cada sessão. Uma sessão pode sobrescrever no painel dela.
        </p>
        <div className="flex flex-col gap-2">
          {draft.agents.map((a) => (
            <div key={a.kind} className="flex flex-wrap items-center gap-2">
              <span className="w-48 text-sm text-gray-300">{KIND_LABEL[a.kind] ?? a.kind}</span>
              <input
                aria-label={`Modelo ${a.kind}`}
                value={a.model}
                onChange={(e) => setAgent(a.kind, { model: e.target.value })}
                className={`${field} w-40`}
              />
              <select
                aria-label={`Effort ${a.kind}`}
                value={a.effort ?? ''}
                onChange={(e) => setAgent(a.kind, { effort: e.target.value || null })}
                className={field}
              >
                <option value="">effort padrão</option>
                {EFFORTS.map((e) => (
                  <option key={e}>{e}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </section>

      <section className={`${card} flex flex-wrap gap-6`}>
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          Sessões abertas ao mesmo tempo
          <input
            type="number"
            min={1}
            value={draft.max_active_sessions}
            onChange={(e) => set('max_active_sessions', Number(e.target.value))}
            className={`${field} w-24`}
          />
          <span className="text-xs text-gray-500">processos claude vivos</span>
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-300">
          Minutos ociosos até dormir
          <input
            type="number"
            min={1}
            value={draft.idle_minutes}
            onChange={(e) => set('idle_minutes', Number(e.target.value))}
            className={`${field} w-24`}
          />
          <span className="text-xs text-gray-500">retoma a conversa na próxima tarefa</span>
        </label>
      </section>

      <section className={card}>
        <h3 className="mb-1 text-sm font-medium text-gray-200">
          MCPs nas sessões de implementação
        </h3>
        <p className="mb-3 text-xs text-gray-500">
          Todos ligados por padrão. Desmarque os que essas sessões não devem carregar.
        </p>
        <div className="mb-3 flex flex-wrap gap-2">
          {servers.map((name) => (
            <label
              key={name}
              className="flex items-center gap-1.5 rounded-md border border-white/10 px-2 py-1 font-mono text-xs text-gray-300"
            >
              <input
                type="checkbox"
                checked={!draft.mcp_disabled.includes(name)}
                onChange={() => toggleMcp(name)}
              />
              {name}
            </label>
          ))}
          {servers.length === 0 && (
            <span className="text-xs text-gray-500">
              Os nomes aparecem aqui depois que uma sessão de implementação conectar.
            </span>
          )}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (mcp.trim()) toggleMcp(mcp.trim())
            setMcp('')
          }}
          className="flex gap-2"
        >
          <input
            aria-label="Desligar MCP"
            placeholder="desligar outro pelo nome"
            value={mcp}
            onChange={(e) => setMcp(e.target.value)}
            className={`${field} w-56 font-mono`}
          />
        </form>
      </section>

      <div className="flex items-center gap-3">
        <button onClick={() => save.mutate(body)} disabled={save.isPending} className={button}>
          Salvar
        </button>
        {save.error && <p className="text-xs text-red-300">{save.error.message}</p>}
        {save.isSuccess && <p className="text-xs text-gray-500">Salvo.</p>}
      </div>
    </>
  )
}
