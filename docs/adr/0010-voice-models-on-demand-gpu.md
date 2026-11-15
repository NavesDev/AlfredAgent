# 0010 — Modelos de voz na GPU sob demanda, com fallback para CPU

- **Status:** Aceito
- **Data:** 2026-11-14

## Contexto

A máquina ganhou uma RTX 3060 (12 GB); antes não havia GPU NVIDIA e tudo rodava na CPU. A GPU é dividida com o serviço `imagens-local`, cujos jobs ocupam até ~10–11 GB e que só cabe um modelo por vez. Issue #5.

Medições com o mesmo áudio (comando de 8 s, `large-v3-turbo`, `beam_size=1`):

| Peça | CPU | GPU |
|---|---|---|
| Whisper | 6,15 s (`int8`) | 0,34 s (`float16`), 0,31 s (`int8_float16`) |
| Whisper, 3 s de áudio | 5,98 s | 0,26 s |
| Kokoro, frase curta (2,5 s de fala) | 0,64 s | 0,07 s |
| Kokoro, 8 s de fala | 2,28 s | 0,14 s |

- Mesmo texto transcrito na CPU e na GPU. `int8_float16` usa ~1,1 GB de VRAM, `float16` ~2,1 GB.
- Whisper custa quase o mesmo para 3 s ou 8 s: o encoder sempre processa a janela de 30 s.
- Carga: Whisper na GPU ~2,6 s (cache em disco); Kokoro troca CPU↔GPU em ~0,07 s. Ao soltar, sobram ~470 MB (contextos CUDA do torch e do CTranslate2).
- Wake word e VAD (openWakeWord, ONNX) ficam na CPU: são minúsculos e rodam por quadro de 80 ms.
- Concorrência: com Whisper + Kokoro residentes (1,86 GB), o `z-image-turbo` 1024 dá OOM ao carregar. Com o Alfred ocioso (só os ~470 MB de contexto) ele gera normal (28 s). Com a GPU cheia, carregar o Whisper falha com OOM.
- Instalação: torch `cu126` traz cuBLAS/cuDNN 9 como wheels `nvidia-*`, que o CTranslate2 também usa. O venv foi de 2,1 GB para 7,5 GB. `cu13x` não serve: o CTranslate2 4.x pede CUDA 12.

## Decisão

- **Dispositivo por modelo** no `config.yaml` (`whisper.device`, `kokoro.device`: `cuda` | `cpu`), padrão `cuda`. Whisper em `int8_float16` na GPU, `int8` na CPU. Modelo continua `large-v3-turbo`: na GPU já sai em 0,3 s, e o `large-v3` cheio teria decoder ~4x mais lento por ganho pequeno em pt.
- **GPU sob demanda** (`infra/audio/device.py`, `OnDemandGpu`):
  - o Whisper carrega na GPU ao ouvir a wake word, enquanto o usuário fala; o Kokoro sobe na primeira fala;
  - cada um solta a GPU depois de `idle_s` sem uso (Whisper 30 s, Kokoro 10 s);
  - só sobe para a GPU se nenhum outro processo tiver ≥ 1 GB nela (job de imagem) e sobrarem 2 GB além do que o modelo precisa. O `nvidia-smi` responde em ~25 ms e não abre contexto CUDA.
- **Fallback, não fail-fast:** GPU ocupada, sem CUDA ou OOM no meio da chamada roda aquela chamada na CPU (modelo de CPU carregado na primeira vez). Depois de uma carga que falhou, fica 60 s na CPU antes de tentar de novo (cada tentativa perdida custa ~2,5 s). Modelo inexistente ainda falha no boot.
- **Transcrição antecipada, não streaming nem blocos de 3 s:** numa pausa de `listener.guess_ms` (400 ms) o Whisper já transcreve o áudio até ali; se ninguém voltar a falar até `silence_ms`, esse texto é o comando. Fala depois do palpite o descarta. Só quando o Whisper está na GPU: na CPU um palpite descartado (~6 s) atrasaria o comando real.
  - Blocos de 3 s custariam o mesmo que o áudio inteiro por bloco (janela de 30 s), cortariam palavras e, na CPU, levariam ~6 s cada.
  - Streaming com re-transcrição contínua gasta GPU o tempo todo para entregar o mesmo texto que o palpite já tem pronto no fim da pausa.

Medido de ponta a ponta (`Listener` real, áudio em tempo real):

| Cenário | Texto pronto após o fim da pausa |
|---|---|
| GPU, com palpite | 0,00 s |
| GPU, sem palpite | 0,32 s |
| GPU ocupada (CPU) | 6,5 s |
| Antes (CPU) | ~6,2 s |

## Consequências

- Do fim da fala ao texto: de ~6 s para ~0 s. O que sobra é o `silence_ms` (1,8 s) e a resposta do Claude. O Kokoro começa a falar em ~0,1 s.
- Um job de imagem nunca trava a voz: o Alfred cai para a CPU e volta à GPU quando ela vaga.
- **Risco aceito:** se o Alfred acabou de usar a GPU (dentro do `idle_s`) e um job de imagem pesado começa a carregar, o job pode dar OOM, e quem tenta de novo é o `imagens-local`. Os ~470 MB de contexto CUDA ficam enquanto o Alfred roda; o `z-image-turbo` em 1536 px, que já trabalhava no limite, pode não caber.
- Baixar `silence_ms` é o próximo ganho de latência, mas corta quem pausa no meio da frase; fica como ajuste do usuário.
- Venv ~5 GB maior; a máquina precisa de driver NVIDIA com CUDA 12+.
