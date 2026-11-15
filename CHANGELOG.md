# Changelog

Mudanças relevantes do Alfred. Formato do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), versões em [SemVer](https://semver.org/lang/pt-BR/). Como lançar: [CONTRIBUTING.md](CONTRIBUTING.md#versões-e-releases).

## [Não lançado]

Primeira versão: voz de ponta a ponta, sessões do Claude Code por projeto, painel e app desktop.

### Voz
- Wake word própria **"Alfred"** (`alfred.onnx`, openWakeWord), com medidor de score para ajuste.
- Transcrição local com Whisper `large-v3-turbo` e fala com Kokoro (pt-BR), na GPU sob demanda, caindo para a CPU se ela estiver ocupada.
- Transcrição adiantada na pausa curta, confirmação falada ("Certo.") assim que você para de falar e bipes de início e fim.
- Responde falando só a linha de resumo; fila de fala, apelidos falados e hotwords com os nomes das sessões.

### Agente principal
- Alfred sobre o Claude Code CLI, com conversa diária retomada e botão "Nova conversa".
- Lê e-mail, agenda, web, navegador, arquivos da home (nunca segredos) e issues do GitHub, sem shell nem edição ([ADR 0003](docs/adr/0003-main-agent-without-exec-tools.md)).
- Fala o que está fazendo enquanto pensa.

### Sessões e projetos
- Sessões nomeadas em paralelo (geral, implementação, sistema), cada uma presa a um projeto e a um ambiente.
- Projetos e ambientes espelhando os git worktrees; `iniciar_feature` abre branch, worktree e sessão de uma vez.
- Delegação por voz ("manda o backend fazer…"), fila por sessão, retratos gerados e descrições curtas.

### Painel e app desktop
- Painel em vidro (estilo visionOS): orbe 3D que reage à voz, transcrição com tempos, sessões, projetos e configurações.
- Uso e limites do plano em anéis, modelo e effort por tipo de agente, MCPs ligáveis por sessão.
- App desktop em Tauri: barra de título própria, tray e pílula flutuante com a esfera e barras de frequência enquanto o Alfred ouve, pensa ou fala ([ADR 0012](docs/adr/0012-desktop-shell-tauri.md)).
- Lançador no menu do sistema (`make install-launcher`).
