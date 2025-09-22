# Agent Notes — VibeVoice Chunk Editor (North Star)

Broad Goal
- Make it effortless to identify, fix, and swap a bad TTS chunk without touching the rest
  of the audio. Keep iteration fast, deterministic, and reversible.

Principles
- Reuse existing code paths for chunking, TTS, crossfades, and stitching.
- Every action updates a single source of truth: project.json.
- Human-friendly chunk indices (chunk_001.flac), zero-padded for stable sorting.
- Editor is always present in the graph; an Active toggle applies or bypasses changes.
- Final mix is built only on explicit request (no surprises).

What “Good” Looks Like
- I can click a timestamp, get the chunk number instantly, flip Active=true, re-gen or
  re-record, and hear the fix in the next final mix.
- Replacing a chunk never corrupts the project; old audio is archived automatically.
- Free mode shifts downstream timing; Locked mode time-stretches to preserve timing.

Non-Goals
- We are not inventing new DSP; we orchestrate the existing pipeline and add metadata.

Future Ideas
- DAW cue markers at chunk boundaries.
- Batch replacement list: [{index, seed}, …].
- Minimal flaceform preview in the node with solo playback for the active chunk.
