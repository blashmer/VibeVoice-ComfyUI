#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="$ROOT_DIR/tests/tmp_project"
rm -rf "$PROJECT_ROOT"
mkdir -p "$PROJECT_ROOT"

export VV_MOCK_TTS=1

SCRIPT_PATH="$ROOT_DIR/examples/sample_script.txt"
PROJECT_DIR="$PROJECT_ROOT/MyProject"

python "$ROOT_DIR/cli/vv-generate-onebyone.py" \
  --script "$SCRIPT_PATH" \
  --out "$PROJECT_DIR" \
  --mock \
  --max-words 12 \
  --force

python "$ROOT_DIR/cli/vv-find-chunk.py" "$PROJECT_DIR/project.json" --ts 1000

IMPORT_CHUNK="$PROJECT_ROOT/import_chunk.flac"
python - "$IMPORT_CHUNK" <<'PY'
import numpy as np
import soundfile as sf
import sys

path = sys.argv[1]
sample_rate = 24000
duration_s = 0.5
t = np.linspace(0.0, duration_s, int(sample_rate * duration_s), endpoint=False)
data = 0.1 * np.sin(2 * np.pi * 220.0 * t).astype("float32")
sf.write(path, data, sample_rate, subtype="PCM_16", format="FLAC")
PY

python "$ROOT_DIR/cli/vv-replace-chunk.py" \
  "$PROJECT_DIR/project.json" \
  --index 1 \
  --mode import \
  --timeline locked \
  --import "$IMPORT_CHUNK" \
  --mock

python "$ROOT_DIR/cli/vv-replace-chunk.py" \
  "$PROJECT_DIR/project.json" \
  --index 2 \
  --mode tts \
  --seed 77 \
  --timeline free \
  --mock

python "$ROOT_DIR/cli/vv-build-final.py" "$PROJECT_DIR/project.json"

FINAL_MIX="$PROJECT_DIR/final_mix.flac"
test -f "$FINAL_MIX"

rm -rf "$PROJECT_ROOT"

echo "Smoke test completed"
