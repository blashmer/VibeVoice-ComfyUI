#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vvproject import find_chunk


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a timestamp to the owning chunk")
    parser.add_argument("project_json", help="Path to project.json")
    parser.add_argument("--ts", type=int, required=True, help="Timestamp in milliseconds")
    args = parser.parse_args()

    project_path = Path(args.project_json).expanduser().resolve()
    if not project_path.exists():
        raise SystemExit(f"Project file not found: {project_path}")

    chunk = find_chunk(project_path, args.ts)
    if chunk is None:
        raise SystemExit("No chunk covers the requested timestamp")

    excerpt = chunk.text.strip()
    if len(excerpt) > 160:
        excerpt = excerpt[:157] + "..."

    payload = {
        "index": chunk.index,
        "filename": chunk.filename,
        "t_start_ms": chunk.t_start_ms,
        "duration_ms": chunk.duration_ms,
        "text_excerpt": excerpt,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
