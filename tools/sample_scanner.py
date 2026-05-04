"""
sample_scanner.py — scan_samples and get_samples MCP tools.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import asyncio

from fastmcp import Context

from config import cache_folder
from classifier import predict_sample_type
from classifier.predict import predict_sample_type_with_meta
from models import Sample, SampleType

AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif"}
CACHE_FILE = "samples_library.json"

# Save cache every N newly processed files
SAVE_INTERVAL = 25

# Stop processing and return partial result after this many seconds
TIMEOUT_SECONDS = 50

# Filename keyword → (type, confidence)
_NAME_RULES: list[tuple[list[str], str, float]] = [
    (["kick", "bd ", " bd_", "_bd_", "_bd.", "bass drum", "bassdrum", "808kick", "kick808"], "kick", 0.92),
    (["snare", "snr", " sn_", "_sn_", "_sn."], "snare", 0.92),
    (["clap", " clp", "_clp"], "clap", 0.92),
    (["hihat_closed", "hihat closed", "hi-hat_closed", "closed hat", "closed_hat",
      "cl_hat", "clhat", "chh", "_chh", "hi hat closed"], "hihat_closed", 0.92),
    (["hihat_open", "hihat open", "hi-hat_open", "open hat", "open_hat",
      "ohh", "_ohh", "hi hat open"], "hihat_open", 0.90),
    (["hihat", "hi-hat", "hi_hat", "hat"], "hihat_closed", 0.80),
    (["crash"], "crash", 0.90),
    (["ride"], "ride", 0.90),
    (["808", "eight08", "sub bass", "subbass", "sub_bass"], "808", 0.90),
    (["tom", " tom"], "tom", 0.88),
    (["perc", "percussion", "conga", "bongo", "shaker", "tamb"], "percussion", 0.85),
    (["fx", " fx_", "_sfx", "riser", "down", "sweep", "impact", "whoosh", "zap"], "fx", 0.80),
]


def _classify_by_name(filename: str) -> tuple[str, float] | None:
    """Return (type, confidence) if the filename clearly identifies the sample type."""
    name = filename.lower()
    for keywords, label, conf in _NAME_RULES:
        if any(kw in name for kw in keywords):
            return label, conf
    return None


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


_SEMAPHORE = asyncio.Semaphore(6)


async def _process_one(audio_file: Path, cache: dict) -> bool:
    """Process a single file. Returns True if newly added."""
    key = str(audio_file)
    if key in cache:
        return False

    # Fast path: classify by filename keyword (no audio loading needed)
    name_result = _classify_by_name(audio_file.name)
    if name_result is not None:
        label, confidence = name_result
        cache[key] = {
            "path": key,
            "filename": audio_file.name,
            "type": label,
            "confidence": confidence,
            "duration": None,
            "bpm": None,
            "brightness": None,
            "rms": None,
            "extension": audio_file.suffix.lower(),
        }
        return True

    # Slow path: load audio and run ML classifier
    async with _SEMAPHORE:
        try:
            label, confidence, duration, brightness, rms_val = await asyncio.to_thread(
                predict_sample_type_with_meta, key
            )

            cache[key] = {
                "path": key,
                "filename": audio_file.name,
                "type": label,
                "confidence": round(confidence, 4),
                "duration": round(duration, 3),
                "bpm": None,
                "brightness": round(brightness, 1),
                "rms": round(rms_val, 6),
                "extension": audio_file.suffix.lower(),
            }
            return True
        except Exception:
            return False


async def scan_samples(
    folder_path: str,
    force_rescan: bool = False,
    ctx: Optional[Context] = None,
) -> dict:
    folder = Path(folder_path)
    if not folder.exists():
        return {"error": f"Folder not found: {folder_path}"}

    cache = _load_cache() if not force_rescan else {}
    cached_before = len(cache)

    audio_files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    ]

    total = len(audio_files)
    if total == 0:
        return {"scanned": 0, "message": "No audio files found in that folder."}

    pending = [f for f in audio_files if str(f) not in cache]
    already_cached = total - len(pending)

    if ctx:
        await ctx.info(
            f"Found {total} files — {already_cached} already cached, {len(pending)} to process."
        )

    if not pending:
        by_type = _breakdown(cache)
        return {
            "scanned": total,
            "new_files": 0,
            "cached_files": already_cached,
            "pending": 0,
            "breakdown_by_type": by_type,
            "cache_path": str(_cache_path()),
            "status": "complete",
        }

    start = time.monotonic()
    new_count = 0
    unsaved_since_last_save = 0
    timed_out = False

    # Process in batches of SAVE_INTERVAL so we flush to disk regularly
    batch: list[asyncio.Task] = []

    async def flush_batch():
        nonlocal new_count, unsaved_since_last_save
        results = await asyncio.gather(*batch, return_exceptions=True)
        for r in results:
            if r is True:
                new_count += 1
                unsaved_since_last_save += 1
        batch.clear()
        if unsaved_since_last_save >= SAVE_INTERVAL:
            _save_cache(cache)
            unsaved_since_last_save = 0

    for i, audio_file in enumerate(pending):
        if time.monotonic() - start > TIMEOUT_SECONDS:
            if batch:
                await flush_batch()
            _save_cache(cache)
            timed_out = True
            processed_so_far = i
            if ctx:
                await ctx.info(
                    f"Timeout reached. Processed {processed_so_far}/{len(pending)} new files. "
                    f"Call scan_samples again to continue — cache is saved."
                )
            break

        batch.append(asyncio.create_task(_process_one(audio_file, cache)))

        if len(batch) >= SAVE_INTERVAL:
            await flush_batch()
            done_total = already_cached + new_count + i + 1 - len(batch)
            if ctx:
                await ctx.report_progress(done_total, total)

    if batch and not timed_out:
        await flush_batch()

    _save_cache(cache)

    remaining = len([f for f in audio_files if str(f) not in cache])

    if ctx and not timed_out:
        await ctx.report_progress(total, total)
        await ctx.info(
            f"Scan complete. {new_count} new files classified, {already_cached} from cache."
        )

    by_type = _breakdown(cache)

    return {
        "scanned": total,
        "new_files": new_count,
        "cached_files": len(cache),
        "pending": remaining,
        "breakdown_by_type": by_type,
        "cache_path": str(_cache_path()),
        "status": "partial — call scan_samples again to continue" if timed_out else "complete",
    }


def _breakdown(cache: dict) -> dict[str, int]:
    by_type: dict[str, int] = {}
    for v in cache.values():
        t = v.get("type", "other")
        by_type[t] = by_type.get(t, 0) + 1
    return by_type


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
        await ctx.info(f"Returning {len(results)} samples (type={type}, min_confidence={min_confidence})")

    return {
        "count": len(results),
        "filters": {"type": type, "min_confidence": min_confidence, "sort_by": sort_by},
        "samples": results,
    }
