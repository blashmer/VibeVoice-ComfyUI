# VibeVoice Targeted Chunk Pipeline

This repository now ships a focused toolchain for building long-form projects from
VibeVoice one chunk at a time. The implementation matches the v1.1 spec for targeted
chunk regeneration and provides identical primitives for both ComfyUI graphs and CLI
automation.

## Runtime Overview

1. **Generate One-By-One** – Split a script into human readable chunks, render them
   sequentially, and persist metadata to `project.json` after each render. Chunk audio
   is written to `chunks/chunk_###.flac` with zero padding for stable sorting.
2. **Find & Edit** – Use the timestamp indexer (CLI) or the `VV Chunk Editor` node to
   select an individual chunk. Archive the previous version to `chunks_archive/` and
   re-render (`mode=tts`) or import a replacement (`mode=import`).
3. **Build Final Mix** – When the user explicitly runs the build command/node the
   current chunk set is crossfaded, loudness-normalised, and written to `final_mix.flac`.

The JSON sidecar is the single source of truth for the current project state. All nodes
and CLIs refresh it atomically so any crash leaves recoverable data on disk.

## Project JSON Schema

```
project.json
├── project
│   ├── sample_rate (Hz)
│   ├── loudness_lufs (target loudness)
│   ├── model_name (VibeVoice checkpoint)
│   ├── global_seed (seed used during the initial render pass)
│   ├── crossfade_ms (overlap between consecutive chunks)
│   ├── chunks_dir (relative folder for active chunk audio)
│   └── final_mix (relative path to final mix file)
└── chunks[]
    ├── index (1-based integer)
    ├── filename (e.g. `chunk_001.flac`)
    ├── text (verbatim script for this chunk)
    ├── char_start / char_end (character offsets within the original script)
    ├── t_start_ms / duration_ms (timeline placement)
    ├── seed (per-chunk RNG seed)
    ├── params (any sampler overrides)
    └── speaker_id (reserved for future multi-voice support)
```

## Audio Processing Details

- **Mock Mode** – Set `VV_MOCK_TTS=1` to bypass model loading and generate deterministic
  synthetic audio. The smoke test harness uses this to avoid large downloads.
- **Crossfades** – During final mix building, a configurable overlap (default 40 ms)
  is applied between consecutive chunks using cosine fade in/out curves.
- **Loudness Normalisation** – The resulting waveform is scaled to the specified LUFS
  target using an RMS-based approximation so that the final mix lands near -16 LUFS.
- **Locked Timeline** – When replacing a chunk with `timeline_mode=locked` the new audio
  is time-stretched to match the previous duration. The default implementation relies on
  `librosa.effects.time_stretch`, which is available through the existing requirements.

## Directory Layout

```
MyProject/
├── project.json
├── chunks/
│   ├── chunk_001.flac
│   └── chunk_002.flac
├── chunks_archive/
│   └── chunk_001__v1.flac
└── final_mix.flac        # Only appears after an explicit build
```

## Automation Entry Points

| Location | Description |
|----------|-------------|
| `cli/vv-generate-onebyone.py` | Generate a project sequentially using the CLI. |
| `cli/vv-find-chunk.py`        | Resolve a timestamp to the owning chunk. |
| `cli/vv-replace-chunk.py`     | Replace a chunk via TTS or import. |
| `cli/vv-build-final.py`       | Build the loudness-normalised final mix. |
| `nodes/vv_project_nodes.py`   | ComfyUI nodes for generate + build. |
| `nodes/vv_chunk_editor.py`    | Always-on editor node with an Active toggle. |

The example workflows under `workflows/` wire these nodes together so new users can
load, run, and observe the complete roundtrip without any manual configuration.
