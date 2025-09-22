from __future__ import annotations

from pathlib import Path
from typing import Tuple

from vvproject.utils import expand_repo_placeholders, ensure_folder_paths, is_mock_mode


class VVChunkEditorNode:
    @classmethod
    def INPUT_TYPES(cls):
        ensure_folder_paths()
        return {
            "required": {
                "project_json": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Absolute path to project.json. {repo} expands to the repo root.",
                    },
                ),
                "index": ("INT", {"default": 1, "min": 1, "max": 10000}),
                "mode": (["tts", "import"], {"default": "tts"}),
                "timeline_mode": (["free", "locked"], {"default": "free"}),
                "active": ("BOOLEAN", {"default": False, "tooltip": "Toggle replacement on/off."}),
            },
            "optional": {
                "seed": ("INT", {"default": -1, "tooltip": "Override seed when >=0"}),
                "cfg_scale": ("FLOAT", {"default": 0.0, "tooltip": "Override cfg_scale when >0"}),
                "diffusion_steps": ("INT", {"default": 0, "tooltip": "Override diffusion steps when >0"}),
                "temperature": ("FLOAT", {"default": 0.0, "tooltip": "Override temperature when >0"}),
                "top_p": ("FLOAT", {"default": 0.0, "tooltip": "Override top_p when >0"}),
                "sampling_mode": (
                    ["project", "true", "false"],
                    {"default": "project", "tooltip": "Override use_sampling"},
                ),
                "import_audio": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Audio file path for import mode. {repo} expands to repo root.",
                        "multiline": False,
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("project_json",)
    FUNCTION = "edit"
    CATEGORY = "VibeVoiceWrapper/Project"
    DESCRIPTION = "Replace a specific chunk via TTS or imported audio"

    def edit(
        self,
        project_json: str,
        index: int,
        mode: str,
        timeline_mode: str,
        active: bool,
        seed: int = -1,
        cfg_scale: float = 0.0,
        diffusion_steps: int = 0,
        temperature: float = 0.0,
        top_p: float = 0.0,
        sampling_mode: str = "project",
        import_audio: str = "",
    ) -> Tuple[str]:
        if not active:
            return (project_json,)

        ensure_folder_paths()
        project_path = Path(expand_repo_placeholders(project_json)).expanduser().resolve()
        if not project_path.exists():
            raise Exception(f"project.json not found: {project_path}")

        overrides = {}
        if cfg_scale > 0:
            overrides["cfg_scale"] = cfg_scale
        if diffusion_steps > 0:
            overrides["diffusion_steps"] = diffusion_steps
        if temperature > 0:
            overrides["temperature"] = temperature
        if top_p > 0:
            overrides["top_p"] = top_p
        if sampling_mode == "true":
            overrides["use_sampling"] = True
        elif sampling_mode == "false":
            overrides["use_sampling"] = False

        import_path = None
        if mode == "import":
            if not import_audio:
                raise Exception("Import mode requires an audio file path")
            import_path = Path(expand_repo_placeholders(import_audio)).expanduser().resolve()
            if not import_path.exists():
                raise Exception(f"Import audio not found: {import_path}")

        chunk_seed = seed if seed is not None and seed >= 0 else None

        from vvproject.engine import replace_chunk

        replace_chunk(
            project_path=project_path,
            index=index,
            mode=mode,
            timeline_mode=timeline_mode,
            seed=chunk_seed,
            overrides=overrides if overrides else None,
            import_path=import_path,
            mock=is_mock_mode(),
        )

        return (str(project_path),)


NODE_CLASS_MAPPINGS = {
    "VVChunkEditorNode": VVChunkEditorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VVChunkEditorNode": "VV Chunk Editor",
}
