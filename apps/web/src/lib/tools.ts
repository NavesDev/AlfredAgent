// Turns raw tool names from agent_progress into what Alfred is doing, in pt-BR.

const RULES: [RegExp, string][] = [
  [/^mcp__alfred__delegar$/, 'Mandando para a sessão sistema'],
  [/^Bash$/, 'Executando um comando'],
  [/^(Read|Glob|Grep)$/, 'Lendo arquivos'],
  [/^(Edit|Write)$/, 'Editando arquivos'],
  [/^WebSearch$/, 'Pesquisando na web'],
  [/^WebFetch$/, 'Lendo uma página'],
  [/Gmail__(search_threads|list_)/, 'Analisando seus e-mails'],
  [/Gmail__/, 'Lendo um e-mail'],
  [/Calendar__suggest_time/, 'Procurando um horário livre'],
  [/Calendar__/, 'Consultando sua agenda'],
  [/chrome-devtools__(new_page|navigate_page)$/, 'Abrindo no navegador'],
  [/chrome-devtools__(take_snapshot|take_screenshot|wait_for)$/, 'Olhando a página'],
  [/chrome-devtools__(click|fill|fill_form|type_text|press_key|hover|drag)$/, 'Mexendo na página'],
  [/chrome-devtools__/, 'Usando o navegador'],
]

export function describeTool(name: string, detail?: string | null): string {
  const label = RULES.find(([pattern]) => pattern.test(name))?.[1] ?? `Usando ${shortName(name)}`
  return detail ? `${label}: ${detail}` : label
}

function shortName(name: string): string {
  return (name.split('__').at(-1) ?? name).replaceAll('_', ' ')
}
