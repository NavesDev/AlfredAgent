# 0012 — App desktop: Tauri v2 embrulhando o painel web

- **Status:** Aceito
- **Data:** 2026-11-14

## Contexto

O painel só abria no navegador: com barra de endereço, sem tray e sem nada na tela quando a janela estava minimizada. O usuário quer janela com topo próprio (sem cabeçalho de navegador nem botões nativos) e um visualizador de voz flutuante quando o app está minimizado ou no tray.

Um spike na máquina do usuário (Zorin/GNOME 46 em X11, RTX 3060) validou o Tauri: janela transparente sem fundo preto, Strands em WebGL2 no WebKitGTK, sempre no topo e clique atravessando a janela.

## Decisão

- **Tauri v2** em `apps/desktop`, casca fina em Rust: janelas, tray, instância única. Sem regra de negócio.
- **Mesma UI:** as janelas carregam o `apps/web` servido em `http://localhost:5173` (o mesmo que o launcher já sobe). Nada de build web embutido.
- **Server separado:** o app não sobe nem para o server; ele é só cliente do `/ws` e da API. Server fora do ar aparece como "Servidor offline" no painel.
- **Janela principal** sem decoração do sistema, cantos arredondados. O `apps/web` desenha a barra de título quando roda no Tauri (`isDesktop()`): faixa transparente que arrasta a janela, título com o ponto de conexão à esquerda e botões redondos de vidro (minimizar, maximizar, fechar) à direita.
- **Fechar esconde no tray.** Sair só pelo menu do tray.
- **Overlay:** segunda janela transparente, sem decoração, sempre no topo, fora da barra de tarefas, que ignora o mouse, no centro-baixo da área útil do monitor principal. Rota `/overlay` do `apps/web`. Fica sempre aberta e sem desenhar nada; mostra a pílula (mini esfera + barras) quando a voz não está `idle` e a janela principal está minimizada ou escondida.
- **Barras com áudio real:** o evento `audio_level` ganha `bands` (9 bandas de frequência da voz, 0..1), calculadas na thread de áudio (mic e TTS). O visualizador é adaptado do Bar Visualizer da ElevenLabs UI (MIT).

## Consequências

- Só X11. No Wayland o GNOME não respeita "sempre no topo" nem posição de janela; o overlay não funcionaria.
- WebKitGTK no lugar do Chromium: diferenças pequenas de CSS e WebGL a vigiar. Plano B é Electron, com troca barata porque a UI inteira fica no `apps/web`.
- Atalho global (push-to-talk) e notificação nativa ficam para depois.
