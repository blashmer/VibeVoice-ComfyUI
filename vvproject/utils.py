from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from typing import Optional


def resolve_repo_root() -> Path:
    """Return the repository root (one level above this module)."""
    return Path(__file__).resolve().parents[1]


def ensure_folder_paths() -> types.ModuleType:
    """Ensure a minimal ``folder_paths`` module exists for CLI usage.

    ComfyUI ships a ``folder_paths`` module that exposes helper functions for
    locating the input/output/temp/model directories. The CLI utilities in this
    repository need the same API even when ComfyUI is not installed, so this
    function provides a lightweight stub that mirrors the interface.
    """
    if "folder_paths" in sys.modules:
        return sys.modules["folder_paths"]

    base_dir = Path(
        os.environ.get(
            "VV_FOLDER_PATHS_BASE",
            Path.home() / ".cache" / "vibevoice_comfyui",
        )
    ).resolve()
    models_dir = base_dir / "models"
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    temp_dir = base_dir / "temp"

    for path in (models_dir, input_dir, output_dir, temp_dir):
        path.mkdir(parents=True, exist_ok=True)

    module = types.ModuleType("folder_paths")
    module.__dict__.update(
        {
            "_base_dir": base_dir,
            "_models_dir": models_dir,
            "_input_dir": input_dir,
            "_output_dir": output_dir,
            "_temp_dir": temp_dir,
            "get_folder_paths": lambda kind: [str(models_dir)]
            if kind == "checkpoints"
            else [str(models_dir)],
            "get_input_directory": lambda: str(input_dir),
            "get_output_directory": lambda: str(output_dir),
            "get_temp_directory": lambda: str(temp_dir),
        }
    )

    sys.modules["folder_paths"] = module
    return module


def expand_repo_placeholders(path_value: str) -> str:
    """Expand ``{repo}`` placeholder tokens in the supplied string."""
    if not path_value:
        return path_value
    repo_root = resolve_repo_root()
    return path_value.replace("{repo}", str(repo_root)).replace("${repo}", str(repo_root))


def load_script_text(script_path: Optional[str], override_text: Optional[str] = None) -> str:
    """Resolve the script text from either an override or a file on disk."""
    if override_text and override_text.strip():
        return override_text

    if script_path:
        expanded = expand_repo_placeholders(script_path)
        candidate = Path(expanded)
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")

    default_script = resolve_repo_root() / "examples" / "sample_script.txt"
    return default_script.read_text(encoding="utf-8")


def is_mock_mode() -> bool:
    """Return ``True`` when synthetic audio should be generated instead of TTS."""
    value = os.environ.get("VV_MOCK_TTS", "")
    return value.lower() not in {"", "0", "false", "off"}
