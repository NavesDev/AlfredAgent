# Training the "Alfred" wake word

Builds `server/wakeword/alfred.onnx` with the openWakeWord training pipeline: thousands of synthetic "Alfred" samples (Piper in English + Kokoro in pt/es/it/fr), augmented with noise and reverb, trained against ~2000 h of precomputed negative speech.

## Cost

| Item | Size / time |
|---|---|
| ACAV100M negative features + validation | ~17 GB |
| Background noise (3000 AudioSet clips) + RIRs | ~1 GB |
| Training venv (torch, speechbrain…) | ~3 GB |
| Generation (~66k clips) + augmentation + training on the CPU (12 cores) | ~1h30 (measured) |

Runs isolated in `.work/` (outside git) with its own venv. It does not affect the server.

## Current result (v3, 2026-10-01)

Evaluated with `evaluate.py` on Kokoro pt-BR voices, threshold 0.5:

| Version | Change | pt-BR (36) | `pm_alex`, voice outside training (12) | False positives (72) |
|---|---|---|---|---|
| v1 | Default recipe, Piper only (English) | 1 | 0 | 0 |
| v2 | `max_negative_weight` 500, target of 1 FP/h | 3 | 1 | 0 |
| v3 | + Kokoro pt/es/it/fr positives (`kokoro_positives.py`) | **17** | **5** | **0** |

Failures cluster on fast speech and on "Alfred, …" run into the sentence. Synthetic voices do not replace a real voice: the next step is testing live and, if needed, training with the user's own recordings.

## Usage

```bash
cd server/wakeword/train
./train.sh            # downloads everything, generates samples, trains and copies the model
```

At the end, point the config at it:

```yaml
wakeword:
  model: wakeword/alfred.onnx
  threshold: 0.5      # tune with real use
```

## Limitations

- The Piper generator uses the LibriTTS multi-speaker model (English). "Brazilianized" spellings ("alfredi", "auf red") sounded like "offered" in Piper and were dropped; the positives are "alfred", "alfredo" and "hey alfred", and similar words ("offered", "afraid") go in as negatives.
- openWakeWord's final `.tflite` conversion needs TensorFlow, which does not support Python 3.11; the script skips that step. The `.onnx` is built before it and is what Alfred uses.
