"""
flp_exporter.py — export_flp tool.

Tries to generate a full .flp FL Studio project using pyflp. If pyflp fails at
any step (version incompatibility, write limitations, etc.), falls back automatically
to MIDI export + a detailed sample assignment guide so the user always gets a result.
"""

from __future__ import annotations

import json
import random
import struct
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

FL_PPQ = 96
SAMPLER_BASE_NOTE = 60  # C5 — no pitch shift in FL Sampler

_KICK_MIDI  = {36}
_SNARE_MIDI = {38, 39}
_HIHAT_MIDI = {42, 46, 49}


# ── Paths ─────────────────────────────────────────────────────────────────────

def _output_dir() -> Path:
    base = cfg.cache_folder().parent / "beats"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _template_path() -> Path:
    cfg_val = cfg.get_config().get("template_flp_path", "")
    if cfg_val:
        return Path(cfg_val)
    return Path(__file__).parent.parent / "template.flp"


def _safe_filename(genre: str, key: str, scale: str, bpm: float, ext: str = "flp") -> str:
    g = genre.replace(" ", "_").replace("/", "_")
    return f"{g}_{key}{scale}_{int(bpm)}bpm.{ext}"


def _beats_to_ticks(beats: float) -> int:
    return int(round(beats * FL_PPQ))


# ── Sample lookup ─────────────────────────────────────────────────────────────

def _get_samples_for_type(sample_type: str) -> list[str]:
    try:
        cache = cfg.cache_folder() / "samples_library.json"
        if not cache.exists():
            return []
        data = json.loads(cache.read_text(encoding="utf-8"))
        return [
            s["path"] for s in data.get("samples", [])
            if s.get("type", "").lower() == sample_type.lower()
            and float(s.get("confidence", 0)) >= 0.65
            and Path(s["path"]).exists()
        ][:3]
    except Exception:
        return []


def _best_sample(sample_type: str) -> str | None:
    paths = _get_samples_for_type(sample_type)
    return paths[0] if paths else None


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


# ── MIDI fallback (same engine as beat_generator) ────────────────────────────

def _export_midi(all_notes: list[dict], path: str, bpm: float) -> None:
    import mido  # type: ignore
    ticks_per_beat = 480
    mid = mido.MidiFile(type=1, ticks_per_beat=ticks_per_beat)
    tracks_map: dict[str, list[dict]] = {}
    for note in all_notes:
        tracks_map.setdefault(note.get("track", "melody"), []).append(note)
    tempo = mido.bpm2tempo(bpm)
    for track_name in ["drums", "bass", "melody", "chords"]:
        track_notes = tracks_map.get(track_name)
        if not track_notes:
            continue
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage("track_name", name=track_name))
        track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
        events: list[tuple[int, object]] = []
        for nd in track_notes:
            ch = int(nd.get("channel", 0))
            n = int(nd["note"])
            v = int(nd.get("velocity", 90))
            st = int(float(nd.get("time", 0)) * ticks_per_beat)
            et = int((float(nd.get("time", 0)) + float(nd.get("duration", 0.25))) * ticks_per_beat)
            events.append((st, mido.Message("note_on",  channel=ch, note=n, velocity=v, time=0)))
            events.append((et, mido.Message("note_off", channel=ch, note=n, velocity=0, time=0)))
        events.sort(key=lambda e: e[0])
        prev = 0
        for abs_t, msg in events:
            msg.time = abs_t - prev
            track.append(msg)
            prev = abs_t
    mid.save(path)


# ── pyflp attempt ─────────────────────────────────────────────────────────────

def _try_pyflp(
    template: Path,
    bpm: float,
    samples: dict,
    drum_notes: list[dict],
    bass_notes: list[dict],
    melody_notes: list[dict],
    chord_notes: list[dict],
    out_path: str,
) -> tuple[bool, str]:
    """
    Attempt to build the .flp using pyflp.
    Returns (success, error_message).
    """
    try:
        import pyflp  # type: ignore
        import pyflp.channel as flp_ch  # type: ignore
    except ImportError:
        return False, "pyflp not installed"

    try:
        project = pyflp.parse(str(template))
    except Exception as exc:
        return False, f"pyflp could not parse template.flp: {exc}"

    # BPM
    try:
        project.tempo = bpm
    except Exception:
        pass

    # Clear template channels
    try:
        while project.channels:
            project.channels.pop()
    except Exception:
        pass

    def _add_sampler(name: str, sample_path: str | None) -> int:
        try:
            ch = flp_ch.Sampler()
            try:
                ch.name = name
            except Exception:
                pass
            if sample_path:
                try:
                    ch.sample_path = sample_path
                except Exception:
                    pass
            project.channels.append(ch)
            return len(project.channels) - 1
        except Exception:
            return -1

    def _add_instrument(name: str) -> int:
        try:
            try:
                ch = flp_ch.Instrument()
            except AttributeError:
                ch = flp_ch.Sampler()
            try:
                ch.name = name
            except Exception:
                pass
            project.channels.append(ch)
            return len(project.channels) - 1
        except Exception:
            return -1

    kick_idx    = _add_sampler("Kick",        samples["kick"])
    snare_idx   = _add_sampler("Snare",       samples["snare"])
    clap_idx    = _add_sampler("Clap",        samples["clap"])
    hihat_idx   = _add_sampler("Hi-Hat",      samples["hihat"])
    open_hh_idx = _add_sampler("Hi-Hat Open", samples["open_hh"])
    crash_idx   = _add_sampler("Crash",       samples["crash"])
    bass_idx    = _add_sampler("808 Bass",    samples["bass_808"]) if samples["bass_808"] else _add_instrument("808 Bass")
    melody_idx  = _add_instrument("Melody")
    chords_idx  = _add_instrument("Chords")

    note_to_ch = {36: kick_idx, 38: snare_idx, 39: clap_idx,
                  42: hihat_idx, 46: open_hh_idx, 49: crash_idx}

    # Get first pattern
    try:
        if not project.patterns:
            import pyflp.pattern as flp_pat  # type: ignore
            project.patterns.append(flp_pat.Pattern())
        pattern = project.patterns[0]
    except Exception as exc:
        return False, f"Cannot access patterns: {exc}"

    def _add_note(pitch: int, time_b: float, dur_b: float, vel: int, ch_idx: int) -> bool:
        if ch_idx < 0:
            return True
        try:
            import pyflp.pattern as flp_pat  # type: ignore
            note = flp_pat.Note()
            note.pitch    = pitch
            note.time     = _beats_to_ticks(time_b)
            note.length   = max(1, _beats_to_ticks(dur_b))
            note.velocity = max(0, min(127, vel))
            for attr in ("rack_channel", "channel"):
                try:
                    setattr(note, attr, ch_idx)
                    break
                except AttributeError:
                    continue
            pattern.notes.append(note)
            return True
        except Exception:
            return False

    for nd in drum_notes:
        ch = note_to_ch.get(int(nd["note"]))
        if ch is not None:
            _add_note(SAMPLER_BASE_NOTE, float(nd["time"]), float(nd.get("duration", 0.125)),
                      int(nd.get("velocity", 90)), ch)

    for nd in bass_notes:
        _add_note(int(nd["note"]), float(nd["time"]), float(nd.get("duration", 0.5)),
                  int(nd.get("velocity", 90)), bass_idx)

    for nd in melody_notes:
        _add_note(int(nd["note"]), float(nd["time"]), float(nd.get("duration", 0.25)),
                  int(nd.get("velocity", 80)), melody_idx)

    for nd in chord_notes:
        _add_note(int(nd["note"]), float(nd["time"]), float(nd.get("duration", 1.0)),
                  int(nd.get("velocity", 75)), chords_idx)

    try:
        pyflp.save(project, out_path)
        return True, ""
    except Exception as exc:
        return False, f"pyflp save failed: {exc}"


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
    Generate a FL Studio project with real drum samples.

    Tries to produce a .flp directly. If pyflp fails (version incompatibility,
    write limitations), falls back to MIDI + a per-channel sample assignment guide
    so the user always gets a working result.
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

    prog_data   = CHORD_PROGRESSIONS.get(genre_lower, CHORD_PROGRESSIONS["hip hop"])
    progression = prog_data["progression"]
    voicing     = prog_data["chord_voicing"]

    # Generate all notes
    drum_notes   = generate_drum_notes(genre_lower, bars)
    bass_notes   = generate_bass_notes(key, resolved_scale, progression, bars, octave=2, genre=genre_lower)
    melody_notes = generate_melody_notes(key, resolved_scale, progression, bars, octave=4, genre=genre_lower)
    chord_notes  = generate_chord_notes(key, resolved_scale, progression, bars, voicing=voicing, octave=3)
    all_notes    = drum_notes + bass_notes + melody_notes + chord_notes

    samples = _collect_samples()
    missing = [k for k, v in samples.items() if not v and k not in ("clap", "open_hh", "crash", "bass_808")]

    # Build the sample assignment guide (used in both success and fallback)
    def _sample_label(key: str, label: str) -> str:
        p = samples.get(key)
        return f"{label}: {p}" if p else f"{label}: (no sample found — assign manually)"

    channel_guide = (
        "Channel Rack — sample assignments:\n"
        f"  [0] {_sample_label('kick',    'Kick')}\n"
        f"  [1] {_sample_label('snare',   'Snare')}\n"
        f"  [2] {_sample_label('clap',    'Clap')}\n"
        f"  [3] {_sample_label('hihat',   'Hi-Hat')}\n"
        f"  [4] {_sample_label('open_hh', 'Hi-Hat Open')}\n"
        f"  [5] {_sample_label('crash',   'Crash')}\n"
        f"  [6] {_sample_label('bass_808','808 Bass')} — or assign 3xOsc\n"
        "  [7] Melody — assign your lead synth\n"
        "  [8] Chords — assign your pad synth\n"
    )

    # ── Try pyflp ────────────────────────────────────────────────────────────

    template = _template_path()
    flp_path: str | None = None
    pyflp_error: str | None = None

    if template.exists():
        if output_path:
            flp_path = output_path
        else:
            flp_path = str(_output_dir() / _safe_filename(genre, key, resolved_scale, bpm, "flp"))

        if ctx:
            await ctx.info(f"Trying pyflp export → {flp_path}")

        ok, pyflp_error = _try_pyflp(
            template, bpm, samples,
            drum_notes, bass_notes, melody_notes, chord_notes,
            flp_path,
        )
        if not ok:
            flp_path = None
            if ctx:
                await ctx.info(f"pyflp failed ({pyflp_error}) — falling back to MIDI")
    else:
        pyflp_error = (
            f"template.flp not found at {template}.\n"
            "Add its path to config.json: \"template_flp_path\": \"C:\\\\...\\\\template.flp\""
        )
        if ctx:
            await ctx.info("No template.flp — exporting MIDI only")

    # ── Always export MIDI ────────────────────────────────────────────────────

    midi_path = str(_output_dir() / _safe_filename(genre, key, resolved_scale, bpm, "mid"))
    try:
        _export_midi(all_notes, midi_path, bpm)
    except Exception as exc:
        return {"error": f"MIDI export failed: {exc}"}

    if ctx:
        await ctx.info(f"MIDI saved: {midi_path}")

    # ── Build result ──────────────────────────────────────────────────────────

    if flp_path:
        instructions = (
            f"Open in FL Studio: File → Open → {flp_path}\n\n"
            + channel_guide
        )
        if missing:
            instructions += f"\nMissing samples: {', '.join(missing)} — run scan_samples first."

        return {
            "success": True,
            "mode": "flp",
            "flp_file": flp_path,
            "midi_file": midi_path,
            "genre": genre,
            "key": key,
            "scale": resolved_scale,
            "bpm": bpm,
            "bars": bars,
            "total_notes": len(all_notes),
            "missing_samples": missing,
            "instructions": instructions,
            "samples": samples,
        }

    # Fallback: MIDI + manual guide
    manual_steps = (
        f"pyflp could not write the .flp ({pyflp_error}).\n"
        "Use the MIDI instead — takes about 2 minutes:\n\n"
        "1. Open FL Studio → open your template.flp\n"
        f"2. File → Import → MIDI file → {midi_path}\n"
        "3. In the Channel Rack, assign one instrument per channel:\n\n"
        + channel_guide + "\n"
        "4. File → Save As → name your project\n\n"
        "Tip: drag each sample file directly from the FL Browser onto its channel."
    )

    if ctx:
        await ctx.info("Done — MIDI ready, pyflp fallback active")

    return {
        "success": True,
        "mode": "midi_fallback",
        "midi_file": midi_path,
        "flp_file": None,
        "pyflp_error": pyflp_error,
        "genre": genre,
        "key": key,
        "scale": resolved_scale,
        "bpm": bpm,
        "bars": bars,
        "total_notes": len(all_notes),
        "missing_samples": missing,
        "instructions": manual_steps,
        "samples": samples,
    }
