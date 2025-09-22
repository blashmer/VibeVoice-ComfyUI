#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vvproject import build_final_mix


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the final mix for a project")
    parser.add_argument("project_json", help="Path to project.json")
    args = parser.parse_args()

    project_path = Path(args.project_json).expanduser().resolve()
    if not project_path.exists():
        raise SystemExit(f"Project file not found: {project_path}")

    final_mix = build_final_mix(project_path)
    print(final_mix)


if __name__ == "__main__":
    main()
