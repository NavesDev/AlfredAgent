# 0001 — Voz local, raciocínio na nuvem

- **Status:** Aceito
- **Data:** 2026-10-01

## Contexto

O Alfred escuta continuamente. Mandar áudio para a nuvem expõe tudo que é dito perto do microfone e adiciona latência e custo. Por outro lado, rodar um LLM competente localmente junto dos ambientes de dev estoura o orçamento de ≤ 3 GB de RAM.

## Decisão

Wake word (openWakeWord), VAD (Silero), STT (faster-whisper) e TTS (Kokoro) rodam 100% locais. Só texto transcrito sai da máquina, para o Claude e para as integrações (Gmail, Calendar, web).

## Consequências

- Áudio nunca sai da máquina.
- Qualidade de transcrição depende do Whisper local: mitigado com `initial_prompt`, apelidos e fuzzy match.
- Pico de ~2 GB de RAM (ou VRAM) no STT; `medium` como plano B.
