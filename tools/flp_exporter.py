"""
flp_exporter.py — export_flp tool.

Generates a complete .flp FL Studio project with:
  - Individual Sampler channels per drum type (kick, snare, hihat, clap)
    each pointing to a real sample file from the user's library.
  - Pattern notes at C5 (no pitch shift) placed at the correct beat positions.
  - Bass, melody, and chord channels with actual MIDI pitches (user assigns synth).

Requires:
  - pyflp: pip install pyflp
  - A template.flp saved in the server root (File → New in FL Studio, then Save As).
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

FL_PPQ = 96  # FL Studio ticks per beat
SAMPLER_BASE_NOTE = 60  # C5 — plays sample at its original pitch

# GM note numbers that generate_drum_notes() emits
_KICK_MIDI  = {36}
_SNARE_MIDI = {38, 39}
_HIHAT_MIDI = {42, 46, 49}
_CLAP_MIDI  = {39}


def _output_dir() -> Path:
    base = cfg.cache_folder().parent / "beats"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _template_path() -> Path:
    # 1. Explicit path in config.json takes priority
    cfg_val = cfg.get_config().get("template_flp_path", "")
    if cfg_val:
        return Path(cfg_val)
    # 2. template.flp next to server.py
    return Path(__file__).parent.parent / "template.flp"


def _safe_filename(genre: str, key: str, scale: str, bpm: float) -> str:
    g = genre.replace(" ", "_").replace("/", "_")
    return f"{g}_{key}{scale}_{int(bpm)}bpm.flp"


def _beats_to_ticks(beats: float) -> int:
    return int(round(beats * FL_PPQ))


def _get_samples_for_type(sample_type: str) -> list[str]:
    """Return file paths from the classifier cache for a given sample type."""
    try:
        cache = cfg.cache_folder() / "samples_library.json"
        if not cache.exists():
            return []
        data = json.loads(cache.read_text(encoding="utf-8"))
        results = [
            s["path"] for s in data.get("samples", [])
            if s.get("type", "").lower() == sample_type.lower()
            and float(s.get("confidence", 0)) >= 0.65
            and Path(s["path"]).exists()
        ]
        return results[:3]
    except Exception:
        return []


def _best_sample(sample_type: str) -> str | None:
    paths = _get_samples_for_type(sample_type)
    return paths[0] if paths else None


def _add_sampler_channel(project, name: str, sample_path: str | None, color: int | None = None):
    """
    Create a Sampler channel with the given sample_path, add it to the project,
    and return the channel index.
    """
    import pyflp.channel as flp_ch  # type: ignore

    sampler = flp_ch.Sampler()
    try:
        sampler.name = name
    except Exception:
        pass

    if sample_path:
        try:
            sampler.sample_path = sample_path
        except Exception:
            pass

    if color is not None:
        try:
            sampler.color = color
        except Exception:
            pass

    project.channels.append(sampler)
    return len(project.channels) - 1


def _add_instrument_channel(project, name: str, color: int | None = None):
    """Add a generic instrument channel (no sample) and return its index."""
    import pyflp.channel as flp_ch  # type: ignore

    try:
        ch = flp_ch.Instrument()
    except AttributeError:
        ch = flp_ch.Sampler()

    try:
        ch.name = name
    except Exception:
        pass

    if color is not None:
        try:
            ch.color = color
        except Exception:
            pass

    project.channels.append(ch)
    return len(project.channels) - 1


def _make_note(pitch: int, time_beats: float, dur_beats: float, velocity: int, rack_channel: int):
    """Build a pyflp Note for the given channel index."""
    import pyflp.pattern as flp_pat  # type: ignore

    note = flp_pat.Note()
    note.pitch = pitch
    note.time = _beats_to_ticks(time_beats)
    note.length = max(1, _beats_to_ticks(dur_beats))
    note.velocity = max(0, min(127, velocity))

    # pyflp 2.x exposes the channel rack index as `rack_channel`
    try:
        note.rack_channel = rack_channel
    except AttributeError:
        try:
            note.channel = rack_channel
        except AttributeError:
            pass

    return note


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
    Generate a full .flp FL Studio project with drum samples and melodic tracks.

    Drums use real sample files from the user's library, one Sampler channel per
    drum type. Bass, melody, and chords are added as pitched channels — the user
    assigns synths to them in FL Studio.
    """
    try:
        import pyflp  # type: ignore
    except ImportError:
        return {"error": "pyflp not installed. Run: pip install pyflp"}

    template = _template_path()
    if not template.exists():
        return {
            "error": (
                f"template.flp not found at: {template}\n\n"
                "Option A — put the file at that exact path:\n"
                "  1. Open FL Studio → File → New → File → Save As\n"
                f"  2. Navigate to: {template.parent}\n"
                "  3. Save as template.flp\n\n"
                "Option B — specify a custom path in config.json:\n"
                '  "template_flp_path": "C:\\\\Users\\\\Yulalo\\\\Desktop\\\\template.flp"\n'
                "  (use double backslashes in JSON)"
            )
        }

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
        return {"error": f"Unknown key: {key!r}. Use note names like C, C#, F#, Bb."}

    if ctx:
        await ctx.info(f"Loading template: {template}")

    try:
        project = pyflp.parse(str(template))
    except Exception as exc:
        return {"error": f"Failed to parse template.flp: {exc}"}

    # Set BPM
    try:
        project.tempo = bpm
    except Exception:
        try:
            project.main_pitch = bpm
        except Exception:
            pass

    # Clear any channels that came from the template so we start fresh
    try:
        while len(project.channels) > 0:
            project.channels.pop()
    except Exception:
        pass

    if ctx:
        await ctx.info("Building channels...")

    # ── Drum channels ─────────────────────────────────────────────────────────

    kick_sample  = _best_sample("kick")
    snare_sample = _best_sample("snare")
    clap_sample  = _best_sample("clap") or snare_sample
    hihat_sample = _best_sample("hihat_closed") or _best_sample("hihat")
    open_hh_sample = _best_sample("hihat_open") or hihat_sample
    crash_sample = _best_sample("crash") or hihat_sample

    # Colors — rough FL Studio palette ints (ABGR hex)
    kick_idx   = _add_sampler_channel(project, "Kick",        kick_sample,    0xFF4040)
    snare_idx  = _add_sampler_channel(project, "Snare",       snare_sample,   0xFF8040)
    clap_idx   = _add_sampler_channel(project, "Clap",        clap_sample,    0xFFB040)
    hihat_idx  = _add_sampler_channel(project, "Hi-Hat",      hihat_sample,   0x40FF40)
    open_hh_idx = _add_sampler_channel(project, "Hi-Hat Open", open_hh_sample, 0x40FFA0)
    crash_idx  = _add_sampler_channel(project, "Crash",       crash_sample,   0x4040FF)

    # 808/bass and melodic channels
    bass_808_sample = _best_sample("808")
    bass_idx    = _add_sampler_channel(project, "808 Bass",   bass_808_sample, 0xFF4080) \
                  if bass_808_sample else _add_instrument_channel(project, "808 Bass", 0xFF4080)
    melody_idx  = _add_instrument_channel(project, "Melody",  0xA040FF)
    chords_idx  = _add_instrument_channel(project, "Chords",  0x40A0FF)

    channel_map = {
        "kick":     kick_idx,
        "snare":    snare_idx,
        "clap":     clap_idx,
        "hihat":    hihat_idx,
        "open_hh":  open_hh_idx,
        "crash":    crash_idx,
        "bass":     bass_idx,
        "melody":   melody_idx,
        "chords":   chords_idx,
    }

    if ctx:
        await ctx.info(f"  {len(project.channels)} channels created")

    # ── Generate music data ───────────────────────────────────────────────────

    prog_data = CHORD_PROGRESSIONS.get(genre_lower, CHORD_PROGRESSIONS["hip hop"])
    progression = prog_data["progression"]
    voicing = prog_data["chord_voicing"]

    drum_notes_raw   = generate_drum_notes(genre_lower, bars)
    bass_notes_raw   = generate_bass_notes(key, resolved_scale, progression, bars, octave=2, genre=genre_lower)
    melody_notes_raw = generate_melody_notes(key, resolved_scale, progression, bars, octave=4, genre=genre_lower)
    chord_notes_raw  = generate_chord_notes(key, resolved_scale, progression, bars, voicing=voicing, octave=3)

    # ── Build pattern notes ───────────────────────────────────────────────────

    # Get or create Pattern 1
    try:
        if not project.patterns:
            import pyflp.pattern as flp_pat  # type: ignore
            pat = flp_pat.Pattern()
            project.patterns.append(pat)
        pattern = project.patterns[0]
    except Exception as exc:
        return {"error": f"Could not access project patterns: {exc}"}

    all_fl_notes = []

    # Drum hits — each note type goes to its matching Sampler channel
    note_to_channel = {
        36: kick_idx,
        38: snare_idx,
        39: clap_idx,
        42: hihat_idx,
        46: open_hh_idx,
        49: crash_idx,
    }

    for nd in drum_notes_raw:
        gm_note = int(nd["note"])
        ch_idx = note_to_channel.get(gm_note)
        if ch_idx is None:
            continue
        fl_note = _make_note(
            pitch=SAMPLER_BASE_NOTE,
            time_beats=float(nd["time"]),
            dur_beats=float(nd.get("duration", 0.125)),
            velocity=int(nd.get("velocity", 90)),
            rack_channel=ch_idx,
        )
        all_fl_notes.append(fl_note)

    for nd in bass_notes_raw:
        fl_note = _make_note(
            pitch=int(nd["note"]),
            time_beats=float(nd["time"]),
            dur_beats=float(nd.get("duration", 0.5)),
            velocity=int(nd.get("velocity", 90)),
            rack_channel=bass_idx,
        )
        all_fl_notes.append(fl_note)

    for nd in melody_notes_raw:
        fl_note = _make_note(
            pitch=int(nd["note"]),
            time_beats=float(nd["time"]),
            dur_beats=float(nd.get("duration", 0.25)),
            velocity=int(nd.get("velocity", 80)),
            rack_channel=melody_idx,
        )
        all_fl_notes.append(fl_note)

    for nd in chord_notes_raw:
        fl_note = _make_note(
            pitch=int(nd["note"]),
            time_beats=float(nd["time"]),
            dur_beats=float(nd.get("duration", 1.0)),
            velocity=int(nd.get("velocity", 75)),
            rack_channel=chords_idx,
        )
        all_fl_notes.append(fl_note)

    # Sort by time and add to pattern
    all_fl_notes.sort(key=lambda n: n.time)
    try:
        for fl_note in all_fl_notes:
            pattern.notes.append(fl_note)
    except Exception as exc:
        return {"error": f"Failed adding notes to pattern: {exc}"}

    if ctx:
        await ctx.info(f"  {len(all_fl_notes)} notes added to Pattern 1")

    # ── Save ─────────────────────────────────────────────────────────────────

    if output_path:
        flp_path = output_path
    else:
        filename = _safe_filename(genre, key, resolved_scale, bpm)
        flp_path = str(_output_dir() / filename)

    try:
        pyflp.save(project, flp_path)
    except Exception as exc:
        return {"error": f"pyflp save failed: {exc}"}

    if ctx:
        await ctx.info(f"Saved: {flp_path}")

    # ── Report missing samples ────────────────────────────────────────────────

    missing: list[str] = []
    if not kick_sample:   missing.append("kick")
    if not snare_sample:  missing.append("snare")
    if not hihat_sample:  missing.append("hihat_closed")

    instructions = (
        "Open in FL Studio:\n"
        "  File → Open → select this .flp file\n\n"
        "Channel Rack layout:\n"
        f"  [0] Kick      → {kick_sample or '⚠ no sample found'}\n"
        f"  [1] Snare     → {snare_sample or '⚠ no sample found'}\n"
        f"  [2] Clap      → {clap_sample or '⚠ no sample found'}\n"
        f"  [3] Hi-Hat    → {hihat_sample or '⚠ no sample found'}\n"
        f"  [4] Hi-Hat Open → {open_hh_sample or '⚠ no sample found'}\n"
        f"  [5] Crash     → {crash_sample or '⚠ no sample found'}\n"
        f"  [6] 808 Bass  → {bass_808_sample or 'assign a synth (e.g. 3xOsc)'}\n"
        "  [7] Melody    → assign your lead synth\n"
        "  [8] Chords    → assign your pad synth\n"
    )

    if missing:
        instructions += (
            f"\n⚠ Missing samples: {', '.join(missing)}\n"
            "Run scan_samples on your samples folder, then call export_flp again."
        )

    return {
        "success": True,
        "flp_file": flp_path,
        "genre": genre,
        "key": key,
        "scale": resolved_scale,
        "bpm": bpm,
        "bars": bars,
        "total_notes": len(all_fl_notes),
        "channels": channel_map,
        "missing_samples": missing,
        "instructions": instructions,
    }
