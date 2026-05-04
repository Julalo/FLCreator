"""
flp_exporter.py — export_flp tool.

Generates a complete FL Studio .flp project using flp_writer.py (pure Python,
no pyflp dependency). Assigns real sample files from the user's library to
individual Sampler channels for each drum type. Bass, melody, and chords are
added as pitched channels — the user assigns synths to them in FL Studio.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from fastmcp import Context

import config as cfg
from tools.music_theory import (
    CHORD_PROGRESSIONS,
    GENRE_BPM,
    SCALES,
    generate_bass_notes,
    generate_chord_notes,
    generate_drum_notes,
    generate_melody_notes,
    get_genre_defaults,
    parse_root,
)
from tools.flp_writer import write_flp, FL_PPQ


# ── Paths ─────────────────────────────────────────────────────────────────────

def _output_dir() -> Path:
    base = cfg.cache_folder().parent / "beats"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_filename(genre: str, key: str, scale: str, bpm: float, ext: str = "flp") -> str:
    g = genre.replace(" ", "_").replace("/", "_")
    return f"{g}_{key}{scale}_{int(bpm)}bpm.{ext}"


def _beats_to_ticks(beats: float) -> int:
    return int(round(beats * FL_PPQ))


# ── Sample lookup ─────────────────────────────────────────────────────────────

def _best_sample(sample_type: str, min_confidence: float = 0.45) -> str | None:
    try:
        cache = cfg.cache_folder() / "samples_library.json"
        if not cache.exists():
            return None
        data = json.loads(cache.read_text(encoding="utf-8"))
        # Cache is a flat dict keyed by path, not {"samples": [...]}
        samples = list(data.values()) if isinstance(data, dict) else data
        results = [
            s["path"] for s in samples
            if isinstance(s, dict)
            and s.get("type", "").lower() == sample_type.lower()
            and float(s.get("confidence", 0)) >= min_confidence
            and Path(s["path"]).exists()
        ]
        return results[0] if results else None
    except Exception:
        return None


def _collect_samples() -> dict:
    return {
        "kick":     _best_sample("kick"),
        "snare":    _best_sample("snare"),
        "clap":     _best_sample("clap") or _best_sample("snare"),
        "hihat":    _best_sample("hihat_closed") or _best_sample("hihat"),
        "open_hh":  _best_sample("hihat_open"),
        "crash":    _best_sample("crash"),
        "bass_808": _best_sample("808"),
    }


# ── Note conversion ───────────────────────────────────────────────────────────

# GM note → rack channel index (matches channel order below)
_GM_TO_CH: dict[int, int] = {
    36: 0,  # kick
    38: 1,  # snare
    39: 2,  # clap
    42: 3,  # hihat closed
    46: 4,  # hihat open
    49: 5,  # crash
}

_SAMPLER_BASE_NOTE = 60  # C5 — plays sample at original pitch


def _build_notes(
    drum_notes: list[dict],
    bass_notes: list[dict],
    melody_notes: list[dict],
    chord_notes: list[dict],
    bass_ch: int,
    melody_ch: int,
    chords_ch: int,
) -> list[dict]:
    result = []

    for nd in drum_notes:
        ch = _GM_TO_CH.get(int(nd["note"]))
        if ch is None:
            continue
        result.append({
            "pos": _beats_to_ticks(float(nd["time"])),
            "len": max(1, _beats_to_ticks(float(nd.get("duration", 0.125)))),
            "key": _SAMPLER_BASE_NOTE,
            "ch":  ch,
            "vel": int(nd.get("velocity", 90)),
        })

    for nd in bass_notes:
        result.append({
            "pos": _beats_to_ticks(float(nd["time"])),
            "len": max(1, _beats_to_ticks(float(nd.get("duration", 0.5)))),
            "key": int(nd["note"]),
            "ch":  bass_ch,
            "vel": int(nd.get("velocity", 90)),
        })

    for nd in melody_notes:
        result.append({
            "pos": _beats_to_ticks(float(nd["time"])),
            "len": max(1, _beats_to_ticks(float(nd.get("duration", 0.25)))),
            "key": int(nd["note"]),
            "ch":  melody_ch,
            "vel": int(nd.get("velocity", 80)),
        })

    for nd in chord_notes:
        result.append({
            "pos": _beats_to_ticks(float(nd["time"])),
            "len": max(1, _beats_to_ticks(float(nd.get("duration", 1.0)))),
            "key": int(nd["note"]),
            "ch":  chords_ch,
            "vel": int(nd.get("velocity", 75)),
        })

    result.sort(key=lambda n: n["pos"])
    return result


# ── Main tool ─────────────────────────────────────────────────────────────────

async def export_flp(
    genre: str,
    key: str,
    bpm: Optional[float],
    bars: int,
    scale_name: Optional[str],
    output_path: Optional[str],
    ctx: Optional[Context],
) -> dict:
    """
    Generate a complete FL Studio .flp project with real drum samples.

    Creates the .flp binary directly — no pyflp or template required.
    Each drum type gets its own Sampler channel with a real sample file.
    Bass, melody, and chords are added as pitched channels.
    """
    genre_lower = genre.lower()
    defaults = get_genre_defaults(genre_lower)

    if bpm is None:
        bpm_range = GENRE_BPM.get(genre_lower, (120, 140))
        bpm = float(random.randint(*bpm_range))
    else:
        bpm = float(bpm)

    resolved_scale = scale_name if scale_name and scale_name in SCALES else defaults["scale"]

    try:
        parse_root(key)
    except ValueError:
        return {"error": f"Unknown key: {key!r}. Use C, C#, F#, Bb, etc."}

    if ctx:
        await ctx.info(f"Building {genre} beat — {key} {resolved_scale} {int(bpm)} BPM {bars} bars")

    # ── Music data ────────────────────────────────────────────────────────────

    prog_data   = CHORD_PROGRESSIONS.get(genre_lower, CHORD_PROGRESSIONS["hip hop"])
    progression = prog_data["progression"]
    voicing     = prog_data["chord_voicing"]

    drum_notes   = generate_drum_notes(genre_lower, bars)
    bass_notes   = generate_bass_notes(key, resolved_scale, progression, bars, octave=2, genre=genre_lower)
    melody_notes = generate_melody_notes(key, resolved_scale, progression, bars, octave=4, genre=genre_lower)
    chord_notes  = generate_chord_notes(key, resolved_scale, progression, bars, voicing=voicing, octave=3)

    # ── Samples ───────────────────────────────────────────────────────────────

    samples = _collect_samples()
    if ctx:
        found = [k for k, v in samples.items() if v]
        missing = [k for k, v in samples.items() if not v and k not in ("clap", "open_hh", "crash", "bass_808")]
        await ctx.info(f"  Samples found: {', '.join(found) or 'none'}")
        if missing:
            await ctx.info(f"  Missing: {', '.join(missing)} (run scan_samples first)")

    # ── Channel definitions ───────────────────────────────────────────────────
    # Order must match _GM_TO_CH (indices 0-5 = drums, 6=bass, 7=melody, 8=chords)

    channels = [
        {"name": "Kick",        "sample_path": samples["kick"],     "color": 0xFF4040},
        {"name": "Snare",       "sample_path": samples["snare"],    "color": 0xFF8040},
        {"name": "Clap",        "sample_path": samples["clap"],     "color": 0xFFB040},
        {"name": "Hi-Hat",      "sample_path": samples["hihat"],    "color": 0x40C040},
        {"name": "Hi-Hat Open", "sample_path": samples["open_hh"],  "color": 0x40C0A0},
        {"name": "Crash",       "sample_path": samples["crash"],    "color": 0x4060FF},
        {"name": "808 Bass",    "sample_path": samples["bass_808"], "color": 0xFF4080},
        {"name": "Melody",      "sample_path": None,                "color": 0xA040FF},
        {"name": "Chords",      "sample_path": None,                "color": 0x40A0FF},
    ]

    bass_ch    = 6
    melody_ch  = 7
    chords_ch  = 8

    # ── Notes ─────────────────────────────────────────────────────────────────

    notes = _build_notes(
        drum_notes, bass_notes, melody_notes, chord_notes,
        bass_ch, melody_ch, chords_ch,
    )

    if ctx:
        await ctx.info(f"  {len(notes)} notes total ({len(drum_notes)} drum hits)")

    # ── Write .flp ────────────────────────────────────────────────────────────

    if output_path:
        flp_path = output_path
    else:
        flp_path = str(_output_dir() / _safe_filename(genre, key, resolved_scale, bpm, "flp"))

    try:
        write_flp(
            output_path=flp_path,
            bpm=bpm,
            channels=channels,
            notes=notes,
            pattern_name=f"{genre.title()} — {key} {resolved_scale}",
        )
    except Exception as exc:
        return {"error": f"Failed to write .flp: {exc}"}

    if ctx:
        await ctx.info(f"Saved: {flp_path}")

    # ── Result ────────────────────────────────────────────────────────────────

    missing_samples = [k for k, v in samples.items() if not v and k not in ("clap", "open_hh", "crash", "bass_808")]

    channel_layout = "\n".join(
        f"  [{i}] {ch['name']} → {ch['sample_path'] or '(assign synth)'}"
        for i, ch in enumerate(channels)
    )

    instructions = (
        f"File → Open → {flp_path}\n\n"
        "Channel Rack:\n"
        + channel_layout
        + ("\n\nMissing samples: run scan_samples, then call export_flp again." if missing_samples else "")
    )

    return {
        "success": True,
        "flp_file": flp_path,
        "genre": genre,
        "key": key,
        "scale": resolved_scale,
        "bpm": bpm,
        "bars": bars,
        "total_notes": len(notes),
        "channels": {ch["name"]: ch["sample_path"] for ch in channels},
        "missing_samples": missing_samples,
        "instructions": instructions,
    }
