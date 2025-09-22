#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vvproject import replace_chunk
from vvproject.utils import ensure_folder_paths, is_mock_mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replace a single chunk within a project")
    parser.add_argument("project_json", help="Path to project.json")
    parser.add_argument("--index", type=int, required=True, help="1-based chunk index to replace")
    parser.add_argument("--mode", choices=["tts", "import"], default="tts", help="Replacement mode")
    parser.add_argument("--timeline", choices=["free", "locked"], default="free", help="Timeline handling")
    parser.add_argument("--seed", type=int, help="Override seed for the replacement")
    parser.add_argument("--cfg", type=float, help="Override cfg_scale for TTS")
    parser.add_argument("--diffusion", type=int, help="Override diffusion steps")
    parser.add_argument("--temperature", type=float, help="Override temperature")
    parser.add_argument("--top-p", type=float, help="Override top-p value")
    parser.add_argument("--sampling", action="store_true", help="Force sampling=True for TTS")
    parser.add_argument("--no-sampling", action="store_true", help="Force sampling=False for TTS")
    parser.add_argument("--import", dest="import_path", help="Audio file to import when mode=import")
    parser.add_argument("--mock", action="store_true", help="Force mock audio generation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_folder_paths()

    project_path = Path(args.project_json).expanduser().resolve()
    if not project_path.exists():
        raise SystemExit(f"Project file not found: {project_path}")

    overrides = {}
    if args.cfg is not None:
        overrides["cfg_scale"] = args.cfg
    if args.diffusion is not None:
        overrides["diffusion_steps"] = args.diffusion
    if args.temperature is not None:
        overrides["temperature"] = args.temperature
    if args.top_p is not None:
        overrides["top_p"] = args.top_p
    if args.sampling:
        overrides["use_sampling"] = True
    if args.no_sampling:
        overrides["use_sampling"] = False

    mock = args.mock or is_mock_mode()

    chunk = replace_chunk(
        project_path=project_path,
        index=args.index,
        mode=args.mode,
        timeline_mode=args.timeline,
        seed=args.seed,
        overrides=overrides if overrides else None,
        import_path=Path(args.import_path).expanduser().resolve() if args.import_path else None,
        mock=mock,
    )

    print(f"Updated chunk {chunk.index} ({chunk.filename})")
    print(f"Seed: {chunk.seed} | Duration: {chunk.duration_ms} ms | Mode: {args.mode}")


if __name__ == "__main__":
    main()
