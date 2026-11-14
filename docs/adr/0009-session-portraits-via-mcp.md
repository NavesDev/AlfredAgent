# 0009 — Retratos das sessões gerados por um agente com os MCPs do usuário

- **Status:** Aceito
- **Data:** 2026-11-14

## Contexto

O painel mostra uma foto por sessão: um retrato 3D estilo massinha (`docs/DESIGN.md`), com o monograma enquanto ele não existe. O usuário já tem geradores de imagem como servidores MCP no Claude Code (hoje o `imagens-local`, na GPU), e pode trocar ou somar outros. Amarrar o Alfred à API de um serviço específico obrigaria código novo a cada gerador.

## Decisão

- **Quem gera:** um agente de uma só pergunta (`infra/claude/portrait.py`, `query()` do Agent SDK), com o modelo do Alfred. Ele recebe um prompt simples (nome da sessão, tipo, projeto e ambiente com as descrições, estilo do retrato) e usa o gerador de imagem que achar entre os MCPs do usuário.
- **Ferramentas:** só MCPs. `tools=[]` tira todas as tools nativas (sem Bash, Read, Write, web). O server lê os MCPs de escopo usuário do Claude Code (`mcpServers` em `~/.claude.json`) e passa só eles (`mcp_servers` + `strict_mcp_config`), com `setting_sources=[]`: sem hooks, plugins, CLAUDE.md nem conectores do claude.ai (Gmail, Drive). `allowed_tools` libera os servidores carregados e `permission_mode="dontAsk"` nega o resto.
- **Gerador favorito (`image_mcp`, em `app_settings`):**
  - definido: só esse servidor é carregado;
  - vazio ("Automático"): carrega todos os servidores de usuário ligados (fora de `mcp_disabled`) e o modelo escolhe o gerador. Na primeira geração que dá certo, o servidor usado vira o favorito. O painel troca o favorito ou volta para "Automático", escolhendo entre os servidores de usuário (`image_mcp_servers`).
- **Imagem:** vem do bloco de imagem do resultado da tool MCP; se o gerador só devolver um caminho, o agente responde `IMAGEM: <caminho>`. O server aceita só PNG, JPEG ou WebP (pelos bytes iniciais), até 20 MB, e copia para `data/portraits/<id da sessão>.<ext>`.
- **Quando:** ao criar a sessão e, no boot, para as sessões sem retrato. Uma geração por vez, numa fila em segundo plano (`controllers/portraits.py`), que nunca bloqueia a criação. `POST /api/sessions/{name}/portrait` pede de novo.
- **Falha** (serviço fora do ar, nenhum gerador, imagem inválida): fica o monograma e o erro vai para o log; tenta de novo no próximo boot ou quando pedirem.
- **Servir:** `GET /api/sessions/{name}/portrait`; `SessionView.portrait` traz essa URL com `?v=<mtime>` (ou `null`). O evento `portrait_updated` faz a sessão republicar o status.

## Consequências

- Trocar de gerador é configurar outro MCP no Claude Code, sem mudar o Alfred.
- **Risco aceito:** sem favorito, a primeira geração pode chamar qualquer MCP de usuário ligado; o prompt só pede uma imagem e não traz conteúdo externo. Depois do primeiro acerto, o favorito restringe ao gerador.
- MCPs de plugin ou do claude.ai não servem de gerador; o gerador precisa estar em `claude mcp add --scope user`.
- O teste real com o `imagens-local` levou ~2 min na primeira geração (carga do modelo na GPU).
- Cada retrato gasta uma chamada curta do modelo do Alfred, além do tempo de GPU.
