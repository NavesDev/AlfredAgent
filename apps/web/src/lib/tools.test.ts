import { describe, expect, it } from 'vitest'
import { describeTool } from './tools'

describe('describeTool', () => {
  it.each([
    ['WebSearch', 'notícias de IA', 'Pesquisando na web: notícias de IA'],
    ['mcp__claude_ai_Gmail__search_threads', null, 'Analisando seus e-mails'],
    ['mcp__claude_ai_Gmail__get_thread', null, 'Lendo um e-mail'],
    ['mcp__claude_ai_Google_Calendar__list_events', null, 'Consultando sua agenda'],
    [
      'mcp__plugin_chrome-devtools-mcp_chrome-devtools__new_page',
      'www.linkedin.com',
      'Abrindo no navegador: www.linkedin.com',
    ],
    ['Bash', 'Gira a tela', 'Executando um comando: Gira a tela'],
    ['mcp__alfred__delegar', null, 'Mandando para a sessão sistema'],
    ['mcp__other__do_thing', null, 'Usando do thing'],
  ])('%s', (name, detail, expected) => {
    expect(describeTool(name, detail)).toBe(expected)
  })
})
