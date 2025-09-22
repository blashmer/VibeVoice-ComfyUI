from __future__ import annotations

import logging
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import utils
from .audio import (
    calculate_duration_ms,
    load_audio,
    match_loudness,
    stitch_chunks,
    time_stretch_to_duration,
    write_flac,
)
from .project import (
    ChunkData,
    ProjectData,
    ProjectSettings,
    find_chunk_by_timestamp,
    load_project,
    recalculate_timeline,
    save_project,
)

utils.ensure_folder_paths()
from nodes.base_vibevoice import BaseVibeVoiceNode  # noqa: E402


LOGGER = logging.getLogger("VibeVoice.Project")


@dataclass
class TTSOptions:
    cfg_scale: float
    diffusion_steps: int
    use_sampling: bool
    temperature: float
    top_p: float

    def as_dict(self) -> Dict[str, object]:
        return {
            "cfg_scale": self.cfg_scale,
            "diffusion_steps": self.diffusion_steps,
            "use_sampling": self.use_sampling,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }


class ChunkRenderer(BaseVibeVoiceNode):
    """Thin wrapper around ``BaseVibeVoiceNode`` for chunk-level rendering."""

    def __init__(self, settings: ProjectSettings, options: TTSOptions, mock: bool = False):
        super().__init__()
        self.settings = settings
        self.options = options
        self.mock = mock
        self._voice_samples = None
        self._speakers = ["Speaker 1"]

    def _ensure_ready(self) -> None:
        if self.mock:
            return
        model_map = self._get_model_mapping()
        model_path = model_map.get(self.settings.model_name, self.settings.model_name)
        self.load_model(self.settings.model_name, model_path, self.settings.attention_type)
        if self._voice_samples is None:
            self._voice_samples = self._prepare_voice_samples(self._speakers, None)

    def render_text(self, text: str, seed: int, overrides: Optional[Dict[str, object]] = None) -> np.ndarray:
        if self.mock:
            return self._render_mock(text, seed)

        self._ensure_ready()
        params = self.options.as_dict()
        if overrides:
            for key, value in overrides.items():
                if value is not None and key in params:
                    if key == "use_sampling":
                        params[key] = bool(value)
                    elif key in {"diffusion_steps"}:
                        params[key] = int(value)
                    else:
                        params[key] = float(value)

        formatted = self._format_text_for_vibevoice(text, self._speakers)
        audio_dict = self._generate_with_vibevoice(
            formatted,
            self._voice_samples,
            params["cfg_scale"],
            seed,
            params["diffusion_steps"],
            params["use_sampling"],
            params["temperature"],
            params["top_p"],
        )

        waveform = audio_dict.get("waveform")
        sample_rate = audio_dict.get("sample_rate", self.settings.sample_rate)

        if hasattr(waveform, "detach"):
            waveform = waveform.detach().cpu().float().numpy()

        if isinstance(waveform, np.ndarray):
            if waveform.ndim == 3:
                data = waveform[0, 0, :]
            elif waveform.ndim == 2:
                data = waveform[0, :]
            else:
                data = waveform
        else:
            data = np.asarray(waveform, dtype=np.float32)

        if sample_rate != self.settings.sample_rate:
            import librosa

            data = librosa.resample(data, orig_sr=sample_rate, target_sr=self.settings.sample_rate)

        return data.astype(np.float32)

    def _render_mock(self, text: str, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        words = max(len(text.split()), 1)
        duration = max(0.35, min(6.0, 0.28 * words))
        num_samples = max(int(round(duration * self.settings.sample_rate)), self.settings.sample_rate // 4)
        t = np.linspace(0.0, duration, num_samples, endpoint=False)
        base_freq = 180.0 + (seed % 7) * 15.0
        waveform = 0.18 * np.sin(2 * math.pi * base_freq * t)
        waveform += 0.08 * np.sin(2 * math.pi * (base_freq * 0.5) * t)
        waveform += 0.05 * rng.standard_normal(num_samples)
        return waveform.astype(np.float32)


def _chunk_script(script_text: str, max_words: int) -> List[Tuple[str, int, int]]:
    helper = BaseVibeVoiceNode()
    raw_chunks = helper._split_text_into_chunks(script_text, max_words)
    positions: List[Tuple[str, int, int]] = []
    cursor = 0
    for raw in raw_chunks:
        chunk_text = raw.strip()
        if not chunk_text:
            continue
        index = script_text.find(chunk_text, cursor)
        if index == -1:
            index = script_text.find(chunk_text)
        if index == -1:
            index = cursor
        start = index
        end = start + len(chunk_text)
        positions.append((chunk_text, start, end))
        cursor = end
    return positions


def _default_tts_options(settings: ProjectSettings) -> TTSOptions:
    defaults = settings.default_params or {}
    return TTSOptions(
        cfg_scale=float(defaults.get("cfg_scale", 1.3)),
        diffusion_steps=int(defaults.get("diffusion_steps", 20)),
        use_sampling=bool(defaults.get("use_sampling", False)),
        temperature=float(defaults.get("temperature", 0.95)),
        top_p=float(defaults.get("top_p", 0.95)),
    )


def _archive_chunk(project: ProjectData, chunk: ChunkData) -> Optional[Path]:
    source = project.chunks_directory / chunk.filename
    if not source.exists():
        return None
    archive_dir = project.archive_directory
    archive_dir.mkdir(parents=True, exist_ok=True)
    stem = source.stem
    existing = sorted(archive_dir.glob(f"{stem}__v*.flac"))
    version = len(existing) + 1
    destination = archive_dir / f"{stem}__v{version}.flac"
    shutil.move(str(source), destination)
    return destination


def generate_project(
    script_text: str,
    project_root: Path,
    settings: ProjectSettings,
    tts_options: TTSOptions,
    max_words_per_chunk: int,
    mock: bool = False,
) -> ProjectData:
    project_root.mkdir(parents=True, exist_ok=True)
    settings.default_params = tts_options.as_dict()
    project = ProjectData(root=project_root, settings=settings, chunks=[])
    project.chunks_directory.mkdir(parents=True, exist_ok=True)
    project.archive_directory.mkdir(parents=True, exist_ok=True)

    renderer = ChunkRenderer(settings, tts_options, mock=mock)
    chunk_specs = _chunk_script(script_text, max_words_per_chunk)

    if not chunk_specs:
        raise ValueError("No chunks produced from script text")

    next_start = 0
    for idx, (chunk_text, char_start, char_end) in enumerate(chunk_specs, start=1):
        seed = settings.global_seed + idx - 1
        audio = renderer.render_text(chunk_text, seed)
        duration_ms = calculate_duration_ms(audio, settings.sample_rate)
        filename = f"chunk_{idx:03d}.flac"
        chunk_path = project.chunks_directory / filename
        write_flac(chunk_path, audio, settings.sample_rate)

        chunk = ChunkData(
            index=idx,
            filename=filename,
            text=chunk_text,
            char_start=char_start,
            char_end=char_end,
            t_start_ms=int(round(next_start)),
            duration_ms=duration_ms,
            seed=seed,
            params=tts_options.as_dict(),
        )
        project.add_chunk(chunk)
        next_start = chunk.t_start_ms + chunk.duration_ms - settings.crossfade_ms
        if next_start < 0:
            next_start = 0
        save_project(project)

    return project


def replace_chunk(
    project_path: Path,
    index: int,
    mode: str,
    timeline_mode: str,
    seed: Optional[int] = None,
    overrides: Optional[Dict[str, object]] = None,
    import_path: Optional[Path] = None,
    mock: bool = False,
) -> ChunkData:
    project = load_project(project_path)
    chunk = project.get_chunk(index)
    if chunk is None:
        raise ValueError(f"Chunk {index} not found")

    archived = _archive_chunk(project, chunk)
    if archived:
        LOGGER.info("Archived %s -> %s", chunk.filename, archived.name)

    target = project.chunks_directory / chunk.filename
    defaults = _default_tts_options(project.settings)

    if mode == "tts":
        renderer = ChunkRenderer(project.settings, defaults, mock=mock)
        chunk_seed = seed if seed is not None else chunk.seed
        audio = renderer.render_text(chunk.text, chunk_seed, overrides)
        params = defaults.as_dict()
        if overrides:
            params.update({k: v for k, v in overrides.items() if v is not None})
        chunk.seed = chunk_seed
        chunk.params = params
    elif mode == "import":
        if import_path is None:
            raise ValueError("Import mode requires an audio file path")
        audio = load_audio(import_path, project.settings.sample_rate)
        params = dict(chunk.params)
        params["mode"] = "import"
        if seed is not None:
            chunk.seed = seed
        chunk.params = params
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    original_duration = chunk.duration_ms
    new_duration = calculate_duration_ms(audio, project.settings.sample_rate)

    if timeline_mode == "locked" and original_duration > 0:
        audio = time_stretch_to_duration(audio, project.settings.sample_rate, original_duration)
        chunk.duration_ms = original_duration
    else:
        chunk.duration_ms = new_duration

    write_flac(target, audio, project.settings.sample_rate)

    if timeline_mode == "free":
        recalculate_timeline(project)

    save_project(project)
    return chunk


def build_final_mix(project_path: Path) -> Path:
    project = load_project(project_path)
    chunk_audios: List[np.ndarray] = []
    for chunk in project.chunks:
        path = project.chunks_directory / chunk.filename
        if not path.exists():
            raise FileNotFoundError(f"Missing chunk audio: {path}")
        chunk_audios.append(load_audio(path, project.settings.sample_rate))

    combined = stitch_chunks(chunk_audios, project.settings.sample_rate, project.settings.crossfade_ms)
    normalised = match_loudness(combined, project.settings.loudness_lufs)
    write_flac(project.final_mix_path, normalised, project.settings.sample_rate)
    return project.final_mix_path


def find_chunk(project_path: Path, timestamp_ms: int) -> Optional[ChunkData]:
    project = load_project(project_path)
    return find_chunk_by_timestamp(project, timestamp_ms)
