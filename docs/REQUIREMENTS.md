# Requisitos

Derivado de [SPEC.md](SPEC.md). Em caso de conflito, a spec vence até este documento ser atualizado.

Convenções: **RF** = requisito funcional, **RNF** = não funcional, **RN** = regra de negócio. Cada item indica a fase do roadmap (F1–F7) em que entra.

## Glossário

| Termo | Significado |
|---|---|
| Wake word | Palavra que ativa a escuta ("Alfred", apelido "Alfredo") |
| Agente principal | Sessão fixa `alfred`: responde, pesquisa, coordena. Não edita código |
| Sessão nomeada | Sessão do Claude Code presa a um workspace; o nome é o "endereço" do comando |
| Projeto | Repositório cadastrado (`repo_path`, `base_branch`, apelidos) |
| Workspace | Diretório de trabalho de um projeto: o `main` ou um `git worktree` |
| Sessão em foco | Sessão que recebe comandos de código sem nome explícito |
| Linha `RESUMO:` | Última linha de cada resposta, até 2 frases, a única lida em voz alta |
| Turno contaminado | Turno em que o agente leu conteúdo externo (e-mail, web) |
| Comando de sistema | Comando resolvido pelo roteador por regex, sem chamar modelo |

## Requisitos funcionais

### Voz

| ID | Requisito | Fase |
|---|---|---|
| RF-01 | Escutar continuamente e ativar com a wake word configurável (`alfred.onnx`, treinado com `server/wakeword/train/`) | F1 |
| RF-02 | Detectar fim de fala com VAD e transcrever localmente com Whisper (pt, `initial_prompt` com jargão) | F1 |
| RF-03 | Falar respostas com Kokoro (voz e velocidade configuráveis) | F1 |
| RF-04 | Ler em voz alta apenas a linha `RESUMO:`; nunca output bruto, código ou caminhos longos | F1 |
| RF-05 | Se a resposta não trouxer `RESUMO:`, gerar resumo com Haiku | F7 |
| RF-06 | Barge-in: wake word durante a fala interrompe o áudio imediatamente | F5 |
| RF-07 | Fila de fala: notificações não atropelam o usuário falando nem outro áudio | F5 |

### Roteamento

| ID | Requisito | Fase |
|---|---|---|
| RF-10 | Interrupções por regex, mesmo com o Alfred ocupado: "para" (cala e cancela o Alfred), "<sessão>, para", "para tudo" | F3 |
| RF-11 | Atalho explícito: frase começando com `<nome>:` ou `<nome>,` de sessão conhecida vai direto para a sessão | F3 |
| RF-12 | Resolução de nome por apelidos + fuzzy match (rapidfuzz, corte ~85%) | F3 |
| RF-13 | Todo o resto vai para o agente principal | F1 |
| RF-14 | Comando para sessão ocupada entra na fila da sessão e o Alfred avisa ("backend tá ocupado, coloquei na fila") | F3 |
| RF-15 | Comandos digitados no painel (`POST /api/commands`) passam pelo mesmo roteador da voz | F6 |

### Agente principal

| ID | Requisito | Fase |
|---|---|---|
| RF-20 | Responder dúvidas de forma curta e falável | F1 |
| RF-21 | Pesquisar na web com WebSearch/WebFetch do Agent SDK | F2 |
| RF-22 | Ler, resumir, buscar e rascunhar e-mails (MCP Gmail) | F2 |
| RF-23 | Ler e consultar eventos (MCP Google Calendar) | F2 |
| RF-24 | Enviar/responder e-mail e alterar eventos somente após confirmação, lendo destinatário e resumo antes | F5 |
| RF-25 | Expor o orquestrador via tools internas (MCP in-process): projetos, sessões, worktrees, tarefas, `delegar` | F3–F4 |
| RF-26 | `delegar(sessao, tarefa)`: envia trabalho a uma sessão nomeada e avisa ao terminar | F3 |
| RF-27 | Comando de código sem nome de sessão vira `delegar(foco, ...)` | F3 |
| RF-28 | Uma conversa por dia: histórico do dia na mesma sessão, nova sessão a cada dia | F1 |

### Sessões, projetos e tarefas

| ID | Requisito | Fase |
|---|---|---|
| RF-30 | Criar, listar, focar, consultar status e fechar sessões nomeadas por voz | F3 |
| RF-31 | Ler o status de todas as sessões numa frase ("Alfred, status") | F3 |
| RF-32 | Ler o último resumo de uma sessão ("backend, o que você fez?") | F3 |
| RF-33 | Interromper a execução de uma sessão ou de todas | F3 |
| RF-34 | Cadastrar e listar projetos com apelidos | F4 |
| RF-35 | Criar worktree (`git worktree add <path> -b <branch>`) e cadastrar o workspace; remover com `git worktree remove` | F4 |
| RF-36 | "Nova sessão X no projeto Y, worktree Z" cria o worktree se não existir e a sessão | F4 |
| RF-37 | Retomar sessões após reiniciar o assistente via `claude_session_id` (resume) | F4 |
| RF-38 | Criar, listar, concluir e priorizar tarefas, com ou sem projeto | F4 |
| RF-39 | Delegar uma tarefa marca-a como `in_progress`; ao fim da sessão, vira `done` automaticamente | F4 |
| RF-40 | Ao terminar, a sessão notifica por voz: "backend terminou: <resumo>" | F3 |

### Permissões e auditoria

| ID | Requisito | Fase |
|---|---|---|
| RF-50 | Denylist sempre negada: `sudo`, `rm -rf` fora do worktree, escrita fora do workspace | F5 |
| RF-51 | Ações sensíveis (push, apagar arquivo, instalar dependência, enviar e-mail, mexer na agenda) pedem confirmação | F5 |
| RF-52 | Canal de confirmação configurável por ação: `voice`, `key`, `web`, `voice+key` | F5 |
| RF-53 | Turno contaminado: qualquer ação com efeito colateral exige confirmação | F5 |
| RF-54 | Sem resposta dentro do timeout (60 s) = negado | F5 |
| RF-55 | Sessão aguardando confirmação fica com status `waiting_permission` | F5 |
| RF-56 | Toda tool call vai para um log de auditoria | F5 |
| RF-57 | Confirmação respondível por voz ou por clique no painel (`POST /api/confirmations/{id}`) | F6 |

### Painel web

| ID | Requisito | Fase |
|---|---|---|
| RF-60 | Dashboard (`/`): sessões, confirmações pendentes, conversa ao vivo, tarefas abertas | F6 |
| RF-61 | Telas `/projects`, `/projects/:id`, `/tasks`, `/activity` | F6 |
| RF-62 | Atualização em tempo real via WebSocket (eventos do bus, incluindo `voice_state` e `audio_level` para animações) | F1 (`/ws`), F6 (painel) |
| RF-63 | CommandBar (Ctrl+K) para falar com o Alfred digitando | F6 |
| RF-64 | Acessível em localhost e pelo celular na rede local | F6 |

## Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | **Privacidade de áudio:** captura, wake word, STT e TTS 100% locais; áudio nunca sai da máquina |
| RNF-02 | **Memória:** ≤ 3 GB de RAM total com 3 sessões ativas (Whisper na GPU reduz ~2 GB) |
| RNF-03 | **Latência de interrupção:** comandos "para" agem em milissegundos, sem chamar modelo |
| RNF-04 | **Custo:** comandos de sistema não gastam tokens; Sonnet por padrão, Haiku para perguntas simples e resumos |
| RNF-05 | **Concorrência:** um processo asyncio; áudio, STT e TTS em threads próprias, sem bloquear o loop dos agentes |
| RNF-06 | **Segurança:** agente principal sem Bash/Edit — quem lê conteúdo externo nunca executa comando |
| RNF-07 | **Resiliência:** reinício do processo não perde projetos, sessões, tarefas nem conversas (SQLite + resume) |
| RNF-08 | **Substituibilidade:** trocar Whisper ou Kokoro mexe só em `listener.py` ou `talker.py`; trocar wake word é trocar o modelo |
| RNF-09 | **Paridade voz/tela:** toda ação e evento disponível por voz aparece no painel e vice-versa, via event bus |
| RNF-10 | **Idioma:** interação em pt-BR; código, pastas e config em inglês |
| RNF-11 | **Rede:** painel apenas na rede local; sem acesso pela internet no MVP |

## Regras de negócio

| ID | Regra |
|---|---|
| RN-01 | Nome de sessão é único no sistema todo |
| RN-02 | Existe sempre uma sessão fixa `alfred` (agente principal), não presa a repositório |
| RN-03 | O agente principal nunca edita código; trabalho em repositório sempre via `delegar` |
| RN-04 | Máximo de 3 sessões de código ativas simultaneamente (configurável) |
| RN-05 | Status de sessão: `idle`, `busy`, `waiting_permission`, `error` |
| RN-06 | Status de tarefa: `open`, `in_progress`, `done`; prioridade `low`, `medium`, `high` |
| RN-07 | Tarefa sem projeto é pessoal ("pagar boleto") |
| RN-08 | Fechar sessão encerra a execução mas mantém o histórico |
| RN-09 | E-mail é sempre lido resumido, nunca na íntegra |
| RN-10 | Ler e-mail/agenda roda direto; escrever exige confirmação |
| RN-11 | Workspace tem `kind` `main` (o próprio repo) ou `worktree` |

## Fora de escopo no MVP

- App desktop com Tauri
- Sandbox das sessões de código
- Acesso pela internet
- Múltiplos usuários
- TTS com clonagem de voz

## Roadmap do MVP

Cada fase entrega algo usável sozinho.

| Fase | Entrega | Critério de pronto |
|---|---|---|
| F1 | Voz de ponta a ponta + wake word `alfred.onnx` treinada + `/ws` de eventos | "Alfred, qual a diferença entre JWT e sessão?" é respondido falando, só o `RESUMO:`; eventos de estado no `/ws` |
| F2 | Assistente geral | Web, Gmail e Calendar funcionando por voz |
| F3 | Sessões nomeadas | 2+ sessões em paralelo, atalho `<nome>:`, foco, status, fila, interrupção |
| F4 | Projetos, worktrees e tarefas | Criar worktree + sessão por voz, delegar tarefa, resume após reinício |
| F5 | Permissões | Confirmação por canal, denylist, turno contaminado, barge-in, fila de notificações, auditoria |
| F6 | Painel web | Telas listadas em RF-60/61, confirmação por clique, CommandBar |
| F7 | Polimento | Wake word refinada com gravações do usuário, verifier opcional com a voz do usuário, `initial_prompt` ajustado, fallback Haiku |

## Questões em aberto

1. **Timeout de permissão duplicado na spec:** `permissions.timeout_s` e `limits.timeout_permissao_s`. Proposta: manter só `permissions.timeout_s`.
2. **Chaves do config em português** (`limites`, `max_sessoes_ativas`) contrariam "config em inglês". Proposta: `limits.max_active_sessions`.
3. **Canal `key`:** qual tecla/dispositivo? Atalho global no desktop exige Tauri (fora do MVP). Proposta: tecla no terminal do server ou botão no painel até lá.
4. **Fila por sessão:** persistida em SQLite ou só em memória? Afeta RNF-07.
5. **Rotação diária da conversa do `alfred`:** em que horário vira o dia, e o que acontece com uma conversa em andamento?
6. **Autenticação do painel na rede local:** nenhuma no MVP? Qualquer um na LAN poderia aprovar confirmações via `web`.
7. **Licença** do projeto.
8. **Uso da assinatura via Agent SDK:** a fase 1 autentica pelo login do Claude Code; confirmar que o uso pessoal é aceito pelos termos, senão migrar para `ANTHROPIC_API_KEY`.
