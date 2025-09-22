from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ProjectSettings:
    sample_rate: int
    loudness_lufs: float
    model_name: str
    attention_type: str
    global_seed: int
    crossfade_ms: int
    chunks_dir: str = "chunks"
    final_mix: str = "final_mix.flac"
    default_params: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        data: Dict[str, object] = {
            "sample_rate": self.sample_rate,
            "loudness_lufs": self.loudness_lufs,
            "model_name": self.model_name,
            "attention_type": self.attention_type,
            "global_seed": self.global_seed,
            "crossfade_ms": self.crossfade_ms,
            "chunks_dir": self.chunks_dir,
            "final_mix": self.final_mix,
        }
        if self.default_params:
            data["default_params"] = self.default_params
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "ProjectSettings":
        default_params = payload.get("default_params", {})
        return cls(
            sample_rate=int(payload.get("sample_rate", 24000)),
            loudness_lufs=float(payload.get("loudness_lufs", -16.0)),
            model_name=str(payload.get("model_name", "VibeVoice-Large")),
            attention_type=str(payload.get("attention_type", "auto")),
            global_seed=int(payload.get("global_seed", 42)),
            crossfade_ms=int(payload.get("crossfade_ms", 40)),
            chunks_dir=str(payload.get("chunks_dir", "chunks")),
            final_mix=str(payload.get("final_mix", "final_mix.flac")),
            default_params=dict(default_params),
        )


@dataclass
class ChunkData:
    index: int
    filename: str
    text: str
    char_start: int
    char_end: int
    t_start_ms: int
    duration_ms: int
    seed: int
    params: Dict[str, object]
    speaker_id: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "index": self.index,
            "filename": self.filename,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "t_start_ms": self.t_start_ms,
            "duration_ms": self.duration_ms,
            "seed": self.seed,
            "params": self.params,
            "speaker_id": self.speaker_id,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "ChunkData":
        return cls(
            index=int(payload["index"]),
            filename=str(payload["filename"]),
            text=str(payload.get("text", "")),
            char_start=int(payload.get("char_start", 0)),
            char_end=int(payload.get("char_end", 0)),
            t_start_ms=int(payload.get("t_start_ms", 0)),
            duration_ms=int(payload.get("duration_ms", 0)),
            seed=int(payload.get("seed", 0)),
            params=dict(payload.get("params", {})),
            speaker_id=int(payload.get("speaker_id", 0)),
        )


@dataclass
class ProjectData:
    root: Path
    settings: ProjectSettings
    chunks: List[ChunkData] = field(default_factory=list)

    @property
    def project_json_path(self) -> Path:
        return self.root / "project.json"

    @property
    def chunks_directory(self) -> Path:
        return self.root / self.settings.chunks_dir

    @property
    def archive_directory(self) -> Path:
        return self.root / "chunks_archive"

    @property
    def final_mix_path(self) -> Path:
        return self.root / self.settings.final_mix

    def to_dict(self) -> Dict[str, object]:
        return {
            "project": self.settings.to_dict(),
            "chunks": [chunk.to_dict() for chunk in sorted(self.chunks, key=lambda c: c.index)],
        }

    def get_chunk(self, index: int) -> Optional[ChunkData]:
        for chunk in self.chunks:
            if chunk.index == index:
                return chunk
        return None

    def add_chunk(self, chunk: ChunkData) -> None:
        existing = self.get_chunk(chunk.index)
        if existing:
            self.chunks.remove(existing)
        self.chunks.append(chunk)
        self.chunks.sort(key=lambda c: c.index)


def save_project(project: ProjectData, path: Optional[Path] = None) -> None:
    target = path or project.project_json_path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fp:
        json.dump(project.to_dict(), fp, indent=2)


def load_project(path: Path) -> ProjectData:
    payload = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    settings = ProjectSettings.from_dict(payload.get("project", {}))
    chunks = [ChunkData.from_dict(entry) for entry in payload.get("chunks", [])]
    project = ProjectData(root=root, settings=settings, chunks=chunks)
    project.chunks.sort(key=lambda c: c.index)
    return project


def recalculate_timeline(project: ProjectData) -> None:
    current_start = 0
    for chunk in sorted(project.chunks, key=lambda c: c.index):
        chunk.t_start_ms = max(int(round(current_start)), 0)
        current_start = chunk.t_start_ms + chunk.duration_ms - project.settings.crossfade_ms
        if current_start < 0:
            current_start = 0


def find_chunk_by_timestamp(project: ProjectData, timestamp_ms: int) -> Optional[ChunkData]:
    for chunk in sorted(project.chunks, key=lambda c: c.index):
        start = chunk.t_start_ms
        end = start + chunk.duration_ms
        if start <= timestamp_ms < end:
            return chunk
    if project.chunks and timestamp_ms >= project.chunks[-1].t_start_ms:
        return project.chunks[-1]
    return None
