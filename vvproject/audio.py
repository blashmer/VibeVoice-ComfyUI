from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import librosa
import numpy as np
import soundfile as sf


def load_audio(path: Path, target_sample_rate: int) -> np.ndarray:
    """Load an audio file as mono float32 data at ``target_sample_rate``."""
    data, sr = sf.read(str(path), always_2d=False)
    if data.ndim > 1:
        data = data[:, 0]
    if sr != target_sample_rate:
        data = librosa.resample(data, orig_sr=sr, target_sr=target_sample_rate)
    return data.astype(np.float32)


def write_flac(path: Path, data: np.ndarray, sample_rate: int) -> None:
    """Write audio data to disk as FLAC, ensuring parent folders exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), data, sample_rate, subtype="PCM_16", format="FLAC")


def calculate_duration_ms(data: np.ndarray, sample_rate: int) -> int:
    """Return the duration of ``data`` in milliseconds."""
    if len(data) == 0:
        return 0
    return int(round(len(data) * 1000.0 / sample_rate))


def rms_loudness_lufs(data: np.ndarray) -> float:
    """Approximate integrated loudness (LUFS) using RMS in dBFS."""
    rms = math.sqrt(float(np.mean(np.square(data)))) if len(data) else 0.0
    if rms <= 0.0:
        return -80.0
    return 20.0 * math.log10(rms + 1e-12)


def match_loudness(data: np.ndarray, target_lufs: float) -> np.ndarray:
    """Scale ``data`` so its RMS-based LUFS approximates ``target_lufs``."""
    current = rms_loudness_lufs(data)
    gain_db = target_lufs - current
    gain = 10 ** (gain_db / 20.0)
    adjusted = data * gain
    return np.clip(adjusted, -1.0, 1.0)


def cosine_crossfade(first: np.ndarray, second: np.ndarray, crossfade_samples: int) -> np.ndarray:
    """Concatenate two signals with a half-cosine crossfade overlap."""
    if crossfade_samples <= 0 or len(first) == 0:
        return np.concatenate([first, second])
    crossfade_samples = min(crossfade_samples, len(first), len(second))
    if crossfade_samples == 0:
        return np.concatenate([first, second])

    fade = np.linspace(0, math.pi / 2.0, crossfade_samples, endpoint=False)
    fade_out = np.cos(fade) ** 2
    fade_in = np.sin(fade) ** 2

    overlap = first[-crossfade_samples:] * fade_out + second[:crossfade_samples] * fade_in
    prefix = first[:-crossfade_samples]
    suffix = second[crossfade_samples:]
    return np.concatenate([prefix, overlap, suffix])


def stitch_chunks(chunk_audios: Iterable[np.ndarray], sample_rate: int, crossfade_ms: int) -> np.ndarray:
    """Apply sequential crossfades across ``chunk_audios``."""
    chunk_list = list(chunk_audios)
    if not chunk_list:
        return np.zeros(0, dtype=np.float32)

    result = chunk_list[0]
    crossfade_samples = int(round(sample_rate * crossfade_ms / 1000.0))
    for chunk in chunk_list[1:]:
        result = cosine_crossfade(result, chunk, crossfade_samples)
    return result


def time_stretch_to_duration(data: np.ndarray, sample_rate: int, target_duration_ms: int) -> np.ndarray:
    """Time-stretch ``data`` so that its duration matches ``target_duration_ms``."""
    if target_duration_ms <= 0 or len(data) == 0:
        return data

    current_duration_ms = calculate_duration_ms(data, sample_rate)
    if current_duration_ms == 0:
        return data

    desired_samples = max(int(round(target_duration_ms * sample_rate / 1000.0)), 1)
    rate = current_duration_ms / float(target_duration_ms)
    stretched = librosa.effects.time_stretch(data, rate=rate)

    if len(stretched) > desired_samples:
        stretched = stretched[:desired_samples]
    elif len(stretched) < desired_samples:
        stretched = np.pad(stretched, (0, desired_samples - len(stretched)))

    return stretched.astype(np.float32)
