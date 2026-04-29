"""
sample_scanner.py — scan_samples and get_samples MCP tools.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import asyncio

from fastmcp import Context

from config import cache_folder
from classifier import predict_sample_type
from models import Sample, SampleType

AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif"}
CACHE_FILE = "samples_library.json"


def _cache_path() -> Path:
    return cache_folder() / CACHE_FILE


def _load_cache() -> dict[str, dict]:
    p = _cache_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(data: dict[str, dict]) -> None:
    _cache_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


async def scan_samples(
    folder_path: str,
    force_rescan: bool = False,
    ctx: Optional[Context] = None,
) -> dict:
    folder = Path(folder_path)
    if not folder.exists():
        return {"error": f"Folder not found: {folder_path}"}

    cache = _load_cache() if not force_rescan else {}

    audio_files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    ]

    total = len(audio_files)
    if total == 0:
        return {"scanned": 0, "message": "No audio files found in that folder."}

    if ctx:
        await ctx.log_info(f"Found {total} audio files in {folder_path}")

    new_count = 0
    for i, audio_file in enumerate(audio_files):
        key = str(audio_file)

        if key in cache:
            # Still report progress even for cached files
            if ctx and i % 50 == 0:
                await ctx.report_progress(i, total)
            continue

        try:
            label, confidence = await asyncio.to_thread(
                predict_sample_type, key
            )

            # Get duration via librosa if available
            duration = 0.0
            bpm = None
            brightness = 0.0
            rms_val = 0.0

            try:
                import librosa  # type: ignore
                import numpy as np
                y, sr = librosa.load(key, sr=22050, mono=True, duration=10.0)
                if len(y) > 0:
                    duration = librosa.get_duration(y=y, sr=sr)
                    brightness = float(
                        librosa.feature.spectral_centroid(y=y, sr=sr).mean()
                    )
                    rms_val = float(librosa.feature.rms(y=y).mean())
                    if label == "loop":
                        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                        bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0]) if len(tempo) > 0 else None
            except Exception:
                pass

            cache[key] = {
                "path": key,
                "filename": audio_file.name,
                "type": label,
                "confidence": round(confidence, 4),
                "duration": round(duration, 3),
                "bpm": round(bpm, 1) if bpm else None,
                "brightness": round(brightness, 1),
                "rms": round(rms_val, 6),
                "extension": audio_file.suffix.lower(),
            }
            new_count += 1

        except Exception as exc:
            if ctx:
                await ctx.log_error(f"Error processing {audio_file.name}: {exc}")

        if ctx and i % 25 == 0:
            await ctx.report_progress(i + 1, total)

    _save_cache(cache)

    if ctx:
        await ctx.report_progress(total, total)
        await ctx.log_info(
            f"Scan complete. {new_count} new files classified, {total - new_count} from cache."
        )

    by_type: dict[str, int] = {}
    for v in cache.values():
        t = v.get("type", "other")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "scanned": total,
        "new_files": new_count,
        "cached_files": total - new_count,
        "breakdown_by_type": by_type,
        "cache_path": str(_cache_path()),
    }


async def get_samples(
    type: Optional[str] = None,
    min_confidence: float = 0.7,
    sort_by: str = "confidence",
    ctx: Optional[Context] = None,
) -> dict:
    cache = _load_cache()
    if not cache:
        return {
            "error": "No samples library found. Run scan_samples first.",
            "samples": [],
        }

    results = list(cache.values())

    if type:
        results = [s for s in results if s.get("type") == type]

    results = [s for s in results if s.get("confidence", 0) >= min_confidence]

    valid_sorts = {"confidence", "brightness", "duration", "bpm"}
    if sort_by not in valid_sorts:
        sort_by = "confidence"

    results.sort(key=lambda s: s.get(sort_by) or 0, reverse=True)

    if ctx:
        await ctx.log_info(f"Returning {len(results)} samples (type={type}, min_confidence={min_confidence})")

    return {
        "count": len(results),
        "filters": {"type": type, "min_confidence": min_confidence, "sort_by": sort_by},
        "samples": results,
    }
