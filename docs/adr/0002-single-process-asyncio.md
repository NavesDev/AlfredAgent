# 0002 — Server em um processo asyncio com event bus em memória

- **Status:** Aceito
- **Data:** 2026-10-01

## Contexto

Voz, agentes, API e WebSocket precisam compartilhar estado (sessões, foco, fila de fala, confirmações pendentes). É um sistema de um usuário, uma máquina.

## Decisão

Um processo Python com asyncio roda o loop dos agentes e o FastAPI. Áudio, STT e TTS rodam em threads próprias. Eventos circulam por um pub/sub em memória (`events.py`) consumido pelo `talker` e pelo `ws.py`.

## Consequências

- Sem IPC, broker nem serialização entre serviços.
- Voz e painel ficam em paridade naturalmente.
- Crash do processo derruba tudo; persistência em SQLite e resume do Agent SDK cobrem o reinício.
- Escalar para múltiplos usuários exigiria rever esta decisão (fora do escopo do MVP).
