#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vvproject import (
    ProjectSettings,
    TTSOptions,
    generate_project,
    load_script_text,
)
from vvproject.utils import ensure_folder_paths, is_mock_mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a VibeVoice project chunk-by-chunk")
    parser.add_argument("--script", required=True, help="Path to the script text file")
    parser.add_argument("--out", required=True, help="Project directory to create")
    parser.add_argument("--sr", type=int, default=24000, help="Sample rate for generated audio")
    parser.add_argument("--lufs", type=float, default=-16.0, help="Target loudness in LUFS")
    parser.add_argument("--xfade", type=int, default=40, help="Crossfade overlap in milliseconds")
    parser.add_argument("--seed", type=int, default=42, help="Global seed for initial render pass")
    parser.add_argument("--model", default="VibeVoice-Large", help="Model name to load")
    parser.add_argument("--attention", default="auto", help="Attention implementation")
    parser.add_argument("--diffusion", type=int, default=20, help="Diffusion steps")
    parser.add_argument("--cfg", type=float, default=1.3, help="Classifier-free guidance scale")
    parser.add_argument("--sampling", action="store_true", help="Enable sampling mode")
    parser.add_argument("--temperature", type=float, default=0.95, help="Sampling temperature")
    parser.add_argument("--top-p", type=float, default=0.95, help="Top-p sampling value")
    parser.add_argument("--max-words", type=int, default=80, help="Maximum words per chunk")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing project directory")
    parser.add_argument("--mock", action="store_true", help="Force mock audio generation (use VV_MOCK_TTS env by default)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_folder_paths()

    project_dir = Path(args.out).expanduser().resolve()
    if project_dir.exists():
        if not args.force and any(project_dir.iterdir()):
            raise SystemExit(f"Project directory {project_dir} already exists. Use --force to overwrite.")
        if args.force:
            shutil.rmtree(project_dir)

    script_text = load_script_text(str(Path(args.script).expanduser().resolve()))

    settings = ProjectSettings(
        sample_rate=args.sr,
        loudness_lufs=args.lufs,
        model_name=args.model,
        attention_type=args.attention,
        global_seed=args.seed,
        crossfade_ms=args.xfade,
    )
    tts_options = TTSOptions(
        cfg_scale=args.cfg,
        diffusion_steps=args.diffusion,
        use_sampling=args.sampling,
        temperature=args.temperature,
        top_p=args.top_p,
    )

    mock = args.mock or is_mock_mode()

    project = generate_project(
        script_text=script_text,
        project_root=project_dir,
        settings=settings,
        tts_options=tts_options,
        max_words_per_chunk=args.max_words,
        mock=mock,
    )

    print(f"Generated {len(project.chunks)} chunks")
    print(project.project_json_path)


if __name__ == "__main__":
    main()
