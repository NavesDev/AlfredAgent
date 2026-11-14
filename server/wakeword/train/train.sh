#!/usr/bin/env bash
# Trains server/wakeword/alfred.onnx. See README.md for disk and time costs.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/.work"
HF="https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main"
PIPER_MODEL="https://github.com/rhasspy/piper-sample-generator/releases/download/v2.0.0/en_US-libritts_r-medium.pt"
mkdir -p "$WORK" && cd "$WORK"

fetch() { [ -s "$2" ] || curl -fL --retry 3 -o "$2" "$1"; }

if [ ! -d .venv ]; then
  uv venv --python 3.11 .venv
  # CPU-only torch: no NVIDIA GPU here, and the CUDA wheels cost ~5 GB of disk
  uv pip install --python .venv --index-url https://download.pytorch.org/whl/cpu \
    "torch==2.5.1" "torchaudio==2.5.1"
  uv pip install --python .venv \
    "openwakeword==0.6.0" torchinfo "torchmetrics<1" "speechbrain<1" \
    "torch-audiomentations<1" acoustics pronouncing "datasets<3" mutagen \
    "deep-phonemizer==0.0.19" "piper-phonemize==1.1.0" webrtcvad onnx "scipy<1.15" tqdm pyyaml httpx "numpy<2" \
    "audiomentations==0.33.0" "setuptools<81"  # webrtcvad imports pkg_resources
fi
PY="$WORK/.venv/bin/python"

[ -d piper-sample-generator ] || git clone -q --branch v2.0.0 https://github.com/rhasspy/piper-sample-generator  # v2 matches openwakeword 0.6 train.py
fetch "$PIPER_MODEL" piper-sample-generator/models/en_US-libritts_r-medium.pt
# HF's CDN stalls single long downloads; pget uses parallel resumable ranges
"$PY" "$HERE/pget.py" "$HF/openwakeword_features_ACAV100M_2000_hrs_16bit.npy" openwakeword_features_ACAV100M_2000_hrs_16bit.npy
"$PY" "$HERE/pget.py" "$HF/validation_set_features.npy" validation_set_features.npy
"$PY" "$HERE/prepare_data.py" "$WORK"
"$PY" -c "import openwakeword.utils as u; u.download_models(['alexa'])"  # melspectrogram/embedding feature models

CONFIG="$HERE/alfred.yml"
"$PY" -m openwakeword.train --training_config "$CONFIG" --generate_clips
# Kokoro runs from the server venv, which already has it and its voices
(cd "$HERE/../.." && PYTHONPATH=. uv run python wakeword/train/kokoro_positives.py "$WORK/output/alfred/positive_train")
# The user's own voice (record_voice.py), if recorded
[ -d "$HERE/voice" ] && "$PY" "$HERE/add_voice.py" "$HERE/voice" "$WORK/output/alfred"
"$PY" -m openwakeword.train --training_config "$CONFIG" --augment_clips --overwrite --train_model \
  || [ -s output/alfred.onnx ]  # the final tflite export needs TensorFlow; the onnx is written before it

cp output/alfred.onnx "$HERE/../alfred.onnx"
echo "ok: $(realpath "$HERE/../alfred.onnx")"
