# Spec — Gerenciador de Agentes por Voz (Claude Code)

30 de set. de 2026 · @Naves

> Spec original do produto. Requisitos rastreáveis em [REQUIREMENTS.md](REQUIREMENTS.md); visão técnica em [ARCHITECTURE.md](ARCHITECTURE.md).

## Visão geral

O Alfred é um assistente pessoal por voz, pensado pra rotina de dev. Ele tira dúvidas, pesquisa na web, lê e-mails e agenda, controla tarefas e gerencia várias sessões do Claude Code em paralelo, cada uma com nome próprio e presa a um projeto e worktree. Você fala "Alfred, backend: cria o endpoint de cancelamento" ou só "Alfred, tenho e-mail importante hoje?" e ele resolve, depois responde falando.

Objetivos:

- Hands-free: escuta contínua com wake word, sem teclado.
- Um ponto de entrada só: o mesmo "Alfred" serve pro dia a dia e pra código.
- Voz 100% local (Whisper + Kokoro); raciocínio e integrações rodam na nuvem.
- Cadastro de projetos, worktrees, sessões nomeadas e tarefas, fácil de chamar por voz.
- Leve o suficiente pra rodar junto dos ambientes de dev (alvo: ≤ 3 GB de RAM no total).

## Arquitetura e stack

A fala desce pela cadeia local até o roteador. Comandos de sistema são resolvidos ali mesmo; o resto vai pro agente principal ou pra uma sessão nomeada, que conversam com o Claude na nuvem e devolvem só a linha de resumo pro Kokoro falar.

## Alfred, o agente principal

Além das sessões de código, existe uma sessão fixa chamada `alfred`: o agente principal. Ela recebe tudo que não for comando de sistema nem tarefa endereçada a uma sessão nomeada. Não fica presa a nenhum repositório; o trabalho dela é responder, buscar e coordenar.

| Capacidade | Como funciona |
|---|---|
| Tirar dúvidas | Resposta direta do modelo, curta e falável |
| Pesquisar na web | Ferramentas WebSearch e WebFetch, nativas do Agent SDK |
| E-mail e agenda | Servidores MCP do Gmail e do Google Calendar: listar, resumir, buscar, rascunhar |
| Tarefas | Ferramentas internas: criar, listar, concluir e priorizar tarefas por projeto |
| Projetos e sessões | Ferramentas internas: listar projetos, criar worktree, abrir sessão, ver status |
| Delegar código | Ferramenta `delegar(sessao, tarefa)`: manda o trabalho pra uma sessão nomeada e avisa quando terminar |

As ferramentas internas são um servidor MCP in-process (o Agent SDK aceita tools Python definidas direto no código) que expõe o próprio orquestrador pro Alfred. Assim ele monta fluxos tipo "pega a tarefa mais urgente do Recurve e manda pro backend" sem você falar com cada peça.

Regras do agente principal:

- Nunca edita código direto; trabalho em repositório sempre vai pra uma sessão nomeada via `delegar`.
- Sabe qual é a sessão em foco e o projeto atual, então "roda os testes" sem nome vira `delegar(foco, ...)`.
- Modelo: Sonnet por padrão pra ficar rápido; perguntas bem simples podem cair no Haiku.
- Contexto: mantém o histórico do dia na mesma sessão e começa uma nova a cada dia, pra não crescer pra sempre.

## Modelo de dados

Três entidades em SQLite: Projeto → Workspace → Sessão. O projeto é só um agrupador; o workspace é uma pasta (com ou sem git) ou um worktree criado a partir de outro workspace. A sessão é o que você chama por voz; o nome dela é o "endereço" do comando.

| Entidade | Campos principais | Exemplo |
|---|---|---|
| Project | id, name, aliases[] | Recurve · aliases: "recurve", "billing" |
| Workspace | id, project_id, name, path, kind (folder ou worktree), parent_id, branch | "back" · ~/dev/recurve-api · folder; "cancelamento" · ~/dev/recurve-api-wt/cancelamento · worktree de back |
| Session | id, name, aliases, kind (geral ou implementacao), workspace_id, model, effort, claude_session_id | "backend" · implementacao · workspace back · opus |
| Task | id, project_id (opcional), title, status, priority, session_id (opcional), created_at | "Implementar reembolso" · Recurve · high · in_progress na sessão backend |

Regras:

- Nome de sessão é único no sistema todo, pra você não precisar falar o projeto toda vez.
- Apelidos existem porque o Whisper às vezes transcreve "backend" como "bequi end"; o match usa apelidos + fuzzy match (rapidfuzz, corte ~85%).
- Nome em inglês num comando em português é o caso mais difícil. Três defesas, nesta ordem: o Whisper recebe os nomes atuais como `hotwords`; apelido de sessão ou projeto achado na transcrição vira o nome real; e o comando chega ao Alfred com uma linha "Nomes conhecidos" para ele escolher o nome mais parecido pelo som, ou perguntar.
- Um projeto pode ter vários workspaces (ex: um pro back e outro pro front). Cadastrar uma pasta não exige git.
- Criar worktree roda `git worktree add <pai>-wt/<nome> -b <nome>` a partir do workspace pai; remover roda `git worktree remove` e recusa se houver mudança não commitada (a menos que force). Remover workspace de pasta comum só tira do cadastro.
- Modelo e effort vêm da tela de configurações por tipo de agente; cada sessão pode sobrescrever.
- O tipo `implementacao` usa o harness completo do Claude Code: CLAUDE.md, skills, plugins, hooks e MCPs ([ADR 0008](adr/0008-implementation-agent-full-harness.md)).
- `claude_session_id` guarda o id do Agent SDK pra retomar a conversa (resume) depois de reiniciar o assistente.
- Status de sessão: ociosa, ocupada, aguardando permissão, erro. Status de tarefa: aberta, em andamento, feita; tarefa sem projeto vale pra coisas pessoais ("pagar boleto"), e tarefa delegada vira feita sozinha quando a sessão termina.

## Comandos de voz e roteamento

Todo comando começa com a wake word. O roteador tenta primeiro os comandos de sistema (regex/gramática fixa, sem gastar token); o que não casar vai pra uma sessão nomeada ou pro agente principal.

| Fala | O que acontece |
|---|---|
| "Alfred, backend: roda os testes do billing" | Envia direto pra sessão "backend" |
| "Alfred, roda os testes" | Agente principal delega pra sessão em foco |
| "Alfred, tenho e-mail importante hoje?" | Lista e resume os e-mails não lidos |
| "Alfred, o que tenho na agenda amanhã?" | Lê os eventos do Google Calendar |
| "Alfred, pesquisa como configurar virtual threads no Spring Boot" | Busca na web e responde em 2 frases |
| "Alfred, qual a diferença entre JWT e sessão?" | Responde direto |
| "Alfred, anota tarefa no Recurve: implementar reembolso" | Cria a tarefa no projeto |
| "Alfred, quais tarefas tenho abertas?" | Lista por projeto e prioridade |
| "Alfred, manda o backend fazer a tarefa de reembolso" | Delega e marca a tarefa como em andamento |
| "Alfred, foca no frontend" | Troca a sessão em foco |
| "Alfred, status" | Lê o status de todas as sessões numa frase |
| "Alfred, backend, o que você fez?" | Lê o último resumo da sessão |
| "Alfred, nova sessão testes no Recurve, worktree cancelamento" | Cria worktree (se não existir) + sessão "testes" |
| "Alfred, cria worktree cancelamento no Recurve" | `git worktree add` + cadastra o workspace |
| "Alfred, lista projetos" / "lista sessões" | Lê os nomes cadastrados |
| "Alfred, backend, para" | Interrompe a execução da sessão |
| "Alfred, fecha a sessão testes" | Encerra a sessão (mantém o histórico) |

Como o roteamento funciona:

1. Interrupções casam por regex e agem em milissegundos, mesmo com o Alfred ocupado: "para" cala a fala e cancela o Alfred, "<sessão>, para" interrompe aquela sessão, "para tudo" interrompe todas.
2. Atalho explícito: frase começando com `<nome>:` ou `<nome>,` de uma sessão conhecida (apelidos + fuzzy match) vai direto pra ela, sem passar pelo Alfred.
3. Todo o resto vai pro agente principal `alfred`, que decide: responde, pesquisa, mexe em e-mail, agenda e tarefas, ou delega pra uma sessão de código. Frases naturais como "pede pro backend rodar os testes" também caem aqui.
4. Tarefa pra sessão ocupada entra na fila dela e o Alfred avisa "backend tá ocupado, coloquei na fila".

## Permissões, notificações e respostas faladas

**Permissões.** As sessões de código rodam no auto mode do Claude Code, que barra sozinho a maior parte das ações perigosas; sem sandbox por enquanto. Por cima disso, o `permissions.py` faz três coisas via `canUseTool`:

- Denylist mínima, sempre negada: `sudo`, `rm -rf` fora do worktree, escrita fora do workspace.
- Ações sensíveis (push, apagar arquivo, instalar dependência, enviar e-mail, mexer na agenda) pedem confirmação pelo canal configurado.
- Turno contaminado: se o Alfred leu e-mail ou web no turno, qualquer ação com efeito colateral exige confirmação, contra prompt injection.

O agente principal não tem Bash nem Edit: quem lê conteúdo externo nunca executa comando. Sessão esperando resposta fica com status aguardando permissão, e toda tool call vai pra um log de auditoria.

O canal de confirmação é configurável por ação, porque um "pode" falado não prova que foi você:

```yaml
permissions:
  default_confirmation: voice      # voice | key | web | voice+key
  per_action:
    git_push: key
    send_email: voice+key
    delete_file: voice
    install_dependency: voice
  tainted_turn: key
  timeout_s: 60                    # no answer = denied
```

**Notificações.** Sessões rodam em background. Ao terminar, o orquestrador fala "backend terminou: <resumo>". Se você estiver falando ou outro áudio estiver tocando, a notificação entra numa fila de fala, sem atropelar.

**Respostas faladas.** O output bruto nunca é lido. O `system_prompt` de cada sessão pede que ela **comece** com uma linha `RESUMO:` de até 2 frases, sem código nem caminhos longos; o TTS lê só essa linha, assim que ela chega no streaming, sem esperar o resto da resposta. Se a linha não vier, o Haiku gera o resumo como fallback.

**E-mail e agenda.** Ler roda direto. Enviar, responder ou mudar evento segue a confirmação configurada, com o Alfred lendo destinatário e resumo antes ("vou responder o João dizendo que topa sexta, posso?"). E-mail é sempre lido resumido, nunca na íntegra.

**Barge-in.** Falar a wake word enquanto o Kokoro fala interrompe o áudio na hora.

## Estrutura, config e recursos

Monorepo com o `server/` na raiz e as interfaces em `apps/`; código, pastas e config em inglês. O server é Python 3.11+, um processo só com asyncio que roda o loop de voz e a API; áudio, STT e TTS ficam em threads próprias pra não travar o loop dos agentes.

A árvore de pastas completa está em [ARCHITECTURE.md](ARCHITECTURE.md#estrutura-de-pastas).

**Server.** `models` guarda dados e SQLite e não sabe nada de voz nem de Claude; `controllers` concentra a lógica de decisão e é o único lugar que junta models com infra; `infra` fala com o mundo externo (microfone, alto-falante, Claude, git); `api` expõe tudo pro painel. Sem interfaces nem camadas extras: trocar Whisper ou Kokoro é mexer só no `listener.py` ou no `talker.py`.

**Event bus.** Os controllers publicam eventos (`transcript`, `session_status`, `task_updated`, `permission_request`, `alfred_reply`) no `events.py`, e o talker e o `ws.py` consomem. Voz e tela ficam em paridade sem duplicar lógica, e um `permission_request` pode ser respondido falando ou clicando no painel (`POST /api/confirmations/{id}`).

**Web (`apps/web`).** React + TypeScript + Vite, Tailwind + shadcn/ui, TanStack Query (o WebSocket atualiza o cache), openapi-typescript + openapi-fetch pra tipos gerados do FastAPI, React Router e Vitest. Em dev o Vite roda separado com proxy; em produção o FastAPI serve o `dist/` numa porta só. Abre em localhost ou no celular pela rede local.

O `src/` é organizado por feature, e toda feature repete o mesmo esqueleto (`pages/`, `components/`, `hooks/`, só com o que ela precisa).

Regras do front:

- Todo acesso à API fica nos hooks da feature (queries e mutations do TanStack Query); componentes só chamam o hook e renderizam.
- Uma feature importa de `api/`, `components/`, `hooks/` e `lib/` globais, nunca de outra feature. A exceção é o dashboard, que existe pra juntar as outras.
- Componente usado por duas features sobe pra `components/`; tipo específico de uma feature vira `types.ts` na raiz dela.
- Sem gerenciador de estado global: estado do servidor no TanStack Query, o resto em `useState`.
- Telas: `/` (dashboard: sessões, confirmações pendentes, conversa ao vivo e tarefas abertas), `/projects`, `/projects/:id`, `/tasks` e `/activity`.
- O CommandBar manda texto pro mesmo router da voz (`POST /api/commands`), pra usar o Alfred digitando quando não dá pra falar.

**Desktop (`apps/desktop`).** Reservado pro Tauri embrulhar o mesmo `apps/web` (bandeja, atalho global, notificação nativa). A arquitetura dele fica pra depois.

Pontos-chave do `config.yaml`:

- whisper: `model: large-v3-turbo`, `device: cuda|cpu`, `compute_type: int8`, `language: pt`, `initial_prompt` com seu jargão (Spring, Liferay, endpoint, worktree, commit, nomes das sessões).
- kokoro: `voice: pf_dora` (ou `pm_alex`), `speed: 1.1`.
- wakeword: nome Alfred, modelo `alfred.onnx` treinado no openWakeWord, threshold 0.65, apelidos alfred e alfredo. É configurável: trocar o nome é apontar pra outro modelo treinado.
- limites: `max_sessoes_ativas: 3`, `timeout_permissao_s: 60`.

| Componente | RAM aprox. | Quando pesa |
|---|---|---|
| openWakeWord + Silero | ~150 MB | Sempre ligado, CPU quase zero |
| faster-whisper large-v3-turbo int8 | ~2 GB (ou ~1,5–2 GB de VRAM na GPU) | Pico curto a cada comando |
| Kokoro | ~400 MB | Só enquanto fala |
| Sessões Claude Code (3) | ~0,5–1 GB | Enquanto rodam tarefas |

Whisper na GPU deixa a RAM praticamente só com as sessões. Se a máquina apertar, trocar pra medium é só mudar uma linha.

## Roadmap do MVP

Cada fase entrega algo usável sozinho:

1. Voz de ponta a ponta: wake word → Whisper → agente principal → Kokoro lendo o `RESUMO:`.
2. Assistente geral: dúvidas, web, Gmail e Google Calendar no agente principal.
3. Sessões nomeadas: SQLite, várias sessões de código, roteamento, foco, status, fila por sessão.
4. Projetos, worktrees e tarefas: cadastro por voz, `git worktree add/remove`, tarefas por projeto, delegar e resume depois de reiniciar.
5. Permissões: confirmação configurável, denylist, turno contaminado, barge-in, fila de notificações.
6. Painel web: `apps/web` com sessões, tarefas, log e confirmação por clique.
7. Polimento: wake word Alfred treinada, ajuste do `initial_prompt`, fallback pro Haiku.

Fora de escopo no MVP: app desktop com Tauri, sandbox das sessões, acesso pela internet, várias pessoas usando e TTS com clonagem de voz.
