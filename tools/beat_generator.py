"""
beat_generator.py — generate_beat and export_to_midi functions.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

from fastmcp import Context

import config as cfg
from tools.music_theory import (
    CHORD_PROGRESSIONS,
    GENRE_BPM,
    MELODY_RHYTHMS,
    SCALES,
    chord_name,
    generate_bass_notes,
    generate_chord_notes,
    generate_drum_notes,
    generate_melody_notes,
    get_genre_defaults,
    parse_root,
)


def _output_dir() -> Path:
    """Return the folder where beat MIDI files are saved."""
    base = cfg.cache_folder().parent / "beats"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_filename(genre: str, key: str, scale: str, bpm: float) -> str:
    safe_genre = genre.replace(" ", "_").replace("/", "_")
    return f"{safe_genre}_{key}{scale}_{int(bpm)}bpm.mid"


def export_to_midi(all_notes: list[dict], output_path: str, bpm: float) -> str:
    """Write a multi-track MIDI file from a flat list of note dicts."""
    try:
        import mido  # type: ignore
    except ImportError:
        raise RuntimeError("mido is not installed — run: pip install mido")

    ticks_per_beat = 480
    mid = mido.MidiFile(type=1, ticks_per_beat=ticks_per_beat)

    # Group notes by track name
    tracks_map: dict[str, list[dict]] = {}
    for note in all_notes:
        track_name = note.get("track", "melody")
        tracks_map.setdefault(track_name, []).append(note)

    track_order = ["drums", "bass", "melody", "chords"]
    # Add any extra tracks not in the standard order
    for name in tracks_map:
        if name not in track_order:
            track_order.append(name)

    tempo = mido.bpm2tempo(bpm)

    for track_name in track_order:
        track_notes = tracks_map.get(track_name)
        if not track_notes:
            continue

        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage("track_name", name=track_name))
        track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

        channel = track_notes[0].get("channel", 0)
        seconds_per_beat = 60.0 / bpm

        # Build list of (absolute_tick, message)
        events: list[tuple[int, object]] = []
        for note_data in track_notes:
            note_num = int(note_data["note"])
            vel = int(note_data.get("velocity", 90))
            start_beats = float(note_data.get("time", 0))
            dur_beats = float(note_data.get("duration", 0.25))
            ch = int(note_data.get("channel", channel))

            start_tick = int(start_beats * ticks_per_beat)
            end_tick = int((start_beats + dur_beats) * ticks_per_beat)

            events.append((start_tick, mido.Message("note_on", channel=ch, note=note_num, velocity=vel, time=0)))
            events.append((end_tick, mido.Message("note_off", channel=ch, note=note_num, velocity=0, time=0)))

        events.sort(key=lambda e: e[0])

        # Convert absolute ticks to delta ticks
        prev_tick = 0
        for abs_tick, msg in events:
            delta = abs_tick - prev_tick
            msg.time = delta
            track.append(msg)
            prev_tick = abs_tick

    mid.save(output_path)
    return output_path


async def generate_beat(
    genre: str,
    key: str,
    bpm: Optional[float],
    bars: int,
    scale_name: Optional[str],
    include: list[str],
    output_path: Optional[str],
    ctx: Optional[Context],
) -> dict:
    """
    Generate a full beat with drums, bass, melody, and chords.

    Returns a dict with the MIDI file path and pattern details.
    """
    genre_lower = genre.lower()
    defaults = get_genre_defaults(genre_lower)

    # Resolve BPM
    if bpm is None:
        bpm_range = GENRE_BPM.get(genre_lower, (120, 140))
        bpm = float(random.randint(*bpm_range))
    else:
        bpm = float(bpm)

    # Resolve scale
    resolved_scale = scale_name if scale_name and scale_name in SCALES else defaults["scale"]

    # Validate key
    try:
        parse_root(key)
    except ValueError:
        return {"error": f"Unknown key: {key!r}. Use note names like C, C#, F#, Bb."}

    if ctx:
        await ctx.info(f"Generating {genre} beat in {key} {resolved_scale} at {bpm} BPM ({bars} bars)...")

    include_lower = [x.lower() for x in include]
    include_all = "all" in include_lower

    prog_data = CHORD_PROGRESSIONS.get(genre_lower, CHORD_PROGRESSIONS["hip hop"])
    progression = prog_data["progression"]
    voicing = prog_data["chord_voicing"]
    bars_per_chord = max(1, bars // len(progression))

    # Build chord names for display
    chord_names = []
    for bar_idx in range(bars):
        chord_idx = (bar_idx // bars_per_chord) % len(progression)
        degree = progression[chord_idx]
        chord_names.append(chord_name(key, resolved_scale, degree))
    chord_display = " — ".join(dict.fromkeys(chord_names))

    all_notes: list[dict] = []
    tracks_info: dict[str, dict] = {}

    if include_all or "drums" in include_lower:
        drum_notes = generate_drum_notes(genre_lower, bars)
        all_notes.extend(drum_notes)
        tracks_info["drums"] = {
            "notes": len(drum_notes),
            "channel": 10,
            "description": f"{genre.title()} drum pattern ({bars} bars)",
        }
        if ctx:
            await ctx.info(f"  Drums: {len(drum_notes)} hits")

    if include_all or "bass" in include_lower:
        bass_style = "walking" if genre_lower in ("lo-fi", "lofi", "house", "jazz") else "root"
        bass_notes = generate_bass_notes(key, resolved_scale, progression, bars, octave=2, style=bass_style)
        all_notes.extend(bass_notes)
        tracks_info["bass"] = {
            "notes": len(bass_notes),
            "channel": 2,
            "description": f"808/bass line — {chord_display}",
        }
        if ctx:
            await ctx.info(f"  Bass: {len(bass_notes)} notes")

    if include_all or "melody" in include_lower:
        melody_notes = generate_melody_notes(key, resolved_scale, progression, bars, octave=4)
        all_notes.extend(melody_notes)
        tracks_info["melody"] = {
            "notes": len(melody_notes),
            "channel": 3,
            "description": f"{key} {resolved_scale} melody",
        }
        if ctx:
            await ctx.info(f"  Melody: {len(melody_notes)} notes")

    if include_all or "chords" in include_lower:
        chord_notes = generate_chord_notes(key, resolved_scale, progression, bars, voicing=voicing, octave=3)
        all_notes.extend(chord_notes)
        tracks_info["chords"] = {
            "notes": len(chord_notes),
            "channel": 4,
            "description": f"Chord pad — {chord_display}",
        }
        if ctx:
            await ctx.info(f"  Chords: {len(chord_notes)} notes")

    if not all_notes:
        return {"error": "No tracks generated. Check the 'include' parameter."}

    # Determine output path
    if output_path:
        midi_path = output_path
    else:
        filename = _safe_filename(genre, key, resolved_scale, bpm)
        midi_path = str(_output_dir() / filename)

    try:
        export_to_midi(all_notes, midi_path, bpm)
    except Exception as exc:
        return {"error": f"MIDI export failed: {exc}"}

    if ctx:
        await ctx.info(f"Beat saved to: {midi_path}")

    # Usage instructions tailored to the OS
    instructions = (
        "Import into FL Studio:\n"
        "  1. File → Import → MIDI file → select the .mid file\n"
        "  2. Each track (drums, bass, melody, chords) will open on a separate channel\n"
        "  3. Assign your favorite instruments/plugins to each channel\n"
        "  4. Drums are on channel 10 (GM standard) — use a drum sampler like FPC or DirectWave\n"
        "  \n"
        "Or send live via LoopMIDI:\n"
        "  Use send_notes with the notes from this beat (one track at a time)"
    )

    return {
        "success": True,
        "midi_file": midi_path,
        "genre": genre,
        "key": key,
        "scale": resolved_scale,
        "bpm": bpm,
        "bars": bars,
        "chord_progression": chord_display,
        "total_notes": len(all_notes),
        "tracks": tracks_info,
        "instructions": instructions,
    }
