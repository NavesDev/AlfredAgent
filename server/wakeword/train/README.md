# Treino da wake word "Alfred"

Gera `server/wakeword/alfred.onnx` com o pipeline de treino do openWakeWord: milhares de amostras sintéticas de "Alfred" (Piper), aumentadas com ruído e reverberação, treinadas contra ~2000 h de fala negativa pré-computada.

## Custo

| Item | Tamanho / tempo |
|---|---|
| Features negativas ACAV100M + validação | ~17 GB |
| Ruído de fundo (3000 clipes do AudioSet) + RIRs | ~1 GB |
| Venv de treino (torch, speechbrain…) | ~3 GB |
| Geração + aumento + treino em CPU (12 cores) | várias horas |

Roda isolado em `.work/` (fora do git) com venv próprio. Não afeta o server.

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
