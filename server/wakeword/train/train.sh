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
  uv pip install --python .venv \
    "openwakeword==0.6.0" "torch<2.6" "torchaudio<2.6" torchinfo "torchmetrics<1" "speechbrain<1" \
    "audiomentations<1" "torch-audiomentations<1" acoustics pronouncing "datasets<3" mutagen \
    "deep-phonemizer==0.0.19" piper-phonemize webrtcvad onnx scipy tqdm pyyaml
fi
PY="$WORK/.venv/bin/python"

[ -d piper-sample-generator ] || git clone --depth 1 https://github.com/rhasspy/piper-sample-generator
fetch "$PIPER_MODEL" piper-sample-generator/models/en_US-libritts_r-medium.pt
fetch "$HF/openwakeword_features_ACAV100M_2000_hrs_16bit.npy" openwakeword_features_ACAV100M_2000_hrs_16bit.npy
fetch "$HF/validation_set_features.npy" validation_set_features.npy
"$PY" "$HERE/prepare_data.py" "$WORK"

"$PY" -m openwakeword.train --training_config "$HERE/alfred.yml" --generate_clips --augment_clips --train_model \
  || [ -s output/alfred.onnx ]  # the final tflite export needs TensorFlow; the onnx is written before it

cp output/alfred.onnx "$HERE/../alfred.onnx"
echo "ok: $(realpath "$HERE/../alfred.onnx")"
