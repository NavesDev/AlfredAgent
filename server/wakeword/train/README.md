# Treino da wake word "Alfred"

Gera `server/wakeword/alfred.onnx` com o pipeline de treino do openWakeWord: milhares de amostras sintéticas de "Alfred" (Piper em inglês + Kokoro em pt/es/it/fr), aumentadas com ruído e reverberação, treinadas contra ~2000 h de fala negativa pré-computada.

## Custo

| Item | Tamanho / tempo |
|---|---|
| Features negativas ACAV100M + validação | ~17 GB |
| Ruído de fundo (3000 clipes do AudioSet) + RIRs | ~1 GB |
| Venv de treino (torch, speechbrain…) | ~3 GB |
| Geração (~66 mil clipes) + aumento + treino em CPU (12 cores) | ~1h30 (medido) |

Roda isolado em `.work/` (fora do git) com venv próprio. Não afeta o server.

## Resultado atual (v3, 2026-10-01)

Avaliado com `evaluate.py` em vozes pt-BR do Kokoro, threshold 0.5:

| Versão | Mudança | pt-BR (36) | `pm_alex`, voz fora do treino (12) | Falsos positivos (72) |
|---|---|---|---|---|
| v1 | Receita padrão, só Piper (inglês) | 1 | 0 | 0 |
| v2 | `max_negative_weight` 500, meta de 1 FP/h | 3 | 1 | 0 |
| v3 | + positivos Kokoro pt/es/it/fr (`kokoro_positives.py`) | **17** | **5** | **0** |

Falhas concentradas em fala rápida e em "Alfred, …" emendado na frase. Vozes sintéticas não substituem a voz real: o próximo passo é testar ao vivo e, se precisar, treinar com gravações do próprio usuário.

## Uso

```bash
cd server/wakeword/train
./train.sh            # baixa tudo, gera amostras, treina e copia o modelo
```

No fim, aponte o config:

```yaml
wakeword:
  model: wakeword/alfred.onnx
  threshold: 0.5      # ajustar no uso real
```

## Limitações

- O gerador do Piper usa o modelo multi-locutor LibriTTS (inglês). Grafias "abrasileiradas" ("alfredi", "auf red") soaram como "offered" no Piper e foram descartadas; os positivos são "alfred", "alfredo" e "hey alfred", e palavras parecidas ("offered", "afraid") entram como negativos.
- A conversão final para `.tflite` do openWakeWord exige TensorFlow, que não suporta Python 3.11; o script ignora essa etapa. O `.onnx` é gerado antes e é o que o Alfred usa.
