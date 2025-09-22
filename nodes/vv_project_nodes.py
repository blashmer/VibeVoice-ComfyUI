from __future__ import annotations

from pathlib import Path
from typing import Tuple

from vvproject.utils import expand_repo_placeholders, ensure_folder_paths, is_mock_mode, load_script_text

ensure_folder_paths()
import folder_paths


class VVGenerateProjectNode:
    @classmethod
    def INPUT_TYPES(cls):
        ensure_folder_paths()
        default_script = "{repo}/examples/sample_script.txt"
        return {
            "required": {
                "script_path": (
                    "STRING",
                    {
                        "default": default_script,
                        "multiline": False,
                        "tooltip": "Path to script file. {repo} expands to the repository root.",
                    },
                ),
                "project_name": (
                    "STRING",
                    {
                        "default": "MyProject",
                        "tooltip": "Project folder name (created inside the ComfyUI output directory).",
                    },
                ),
                "sample_rate": (
                    "INT",
                    {"default": 24000, "min": 8000, "max": 96000, "step": 1000},
                ),
                "loudness_lufs": ("FLOAT", {"default": -16.0, "step": 0.5}),
                "crossfade_ms": ("INT", {"default": 40, "min": 0, "max": 500, "step": 5}),
                "global_seed": ("INT", {"default": 42, "min": 0, "max": 2**32 - 1}),
                "model": (
                    ["VibeVoice-1.5B", "VibeVoice-Large", "VibeVoice-Large-Quant-4Bit"],
                    {"default": "VibeVoice-Large"},
                ),
                "attention_type": (
                    ["auto", "eager", "sdpa", "flash_attention_2", "sage"],
                    {"default": "auto"},
                ),
                "diffusion_steps": ("INT", {"default": 20, "min": 5, "max": 100, "step": 1}),
                "cfg_scale": ("FLOAT", {"default": 1.3, "min": 0.5, "max": 3.5, "step": 0.05}),
                "use_sampling": ("BOOLEAN", {"default": False}),
                "temperature": ("FLOAT", {"default": 0.95, "min": 0.1, "max": 2.0, "step": 0.05}),
                "top_p": ("FLOAT", {"default": 0.95, "min": 0.1, "max": 1.0, "step": 0.05}),
                "max_words_per_chunk": ("INT", {"default": 80, "min": 5, "max": 400, "step": 5}),
                "active": ("BOOLEAN", {"default": True, "tooltip": "Disable to skip generation."}),
            },
            "optional": {
                "script_text": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Optional inline script override.",
                        "forceInput": False,
                    },
                )
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("project_json",)
    FUNCTION = "generate"
    CATEGORY = "VibeVoiceWrapper/Project"
    DESCRIPTION = "Generate a chunked VibeVoice project (one chunk per file)"

    def generate(
        self,
        script_path: str,
        project_name: str,
        sample_rate: int,
        loudness_lufs: float,
        crossfade_ms: int,
        global_seed: int,
        model: str,
        attention_type: str,
        diffusion_steps: int,
        cfg_scale: float,
        use_sampling: bool,
        temperature: float,
        top_p: float,
        max_words_per_chunk: int,
        active: bool,
        script_text: str = "",
    ) -> Tuple[str]:
        if not active:
            project_dir = Path(folder_paths.get_output_directory()) / project_name
            return (str((project_dir / "project.json").resolve()),)

        ensure_folder_paths()
        output_root = Path(folder_paths.get_output_directory()).resolve()
        project_dir = output_root / project_name
        if project_dir.exists() and any(project_dir.iterdir()):
            raise Exception(f"Project directory already exists and is not empty: {project_dir}")

        script = load_script_text(expand_repo_placeholders(script_path), script_text)

        from vvproject.project import ProjectSettings
        from vvproject.engine import TTSOptions, generate_project

        settings = ProjectSettings(
            sample_rate=sample_rate,
            loudness_lufs=loudness_lufs,
            model_name=model,
            attention_type=attention_type,
            global_seed=global_seed,
            crossfade_ms=crossfade_ms,
        )
        options = TTSOptions(
            cfg_scale=cfg_scale,
            diffusion_steps=diffusion_steps,
            use_sampling=use_sampling,
            temperature=temperature,
            top_p=top_p,
        )

        project = generate_project(
            script_text=script,
            project_root=project_dir,
            settings=settings,
            tts_options=options,
            max_words_per_chunk=max_words_per_chunk,
            mock=is_mock_mode(),
        )

        return (str(project.project_json_path.resolve()),)


class VVBuildFinalMixNode:
    @classmethod
    def INPUT_TYPES(cls):
        ensure_folder_paths()
        return {
            "required": {
                "project_json": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Absolute path to project.json",
                    },
                ),
                "active": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("final_mix",)
    FUNCTION = "build"
    CATEGORY = "VibeVoiceWrapper/Project"
    DESCRIPTION = "Concatenate all chunks, apply crossfades and loudness normalisation"

    def build(self, project_json: str, active: bool) -> Tuple[str]:
        if not active:
            return (project_json,)

        ensure_folder_paths()
        from vvproject import build_final_mix

        project_path = Path(expand_repo_placeholders(project_json)).expanduser().resolve()
        if not project_path.exists():
            raise Exception(f"project.json not found: {project_path}")

        final_mix = build_final_mix(project_path)
        return (str(final_mix.resolve()),)


NODE_CLASS_MAPPINGS = {
    "VVGenerateProjectNode": VVGenerateProjectNode,
    "VVBuildFinalMixNode": VVBuildFinalMixNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VVGenerateProjectNode": "VV Generate Project",
    "VVBuildFinalMixNode": "VV Build Final Mix",
}
