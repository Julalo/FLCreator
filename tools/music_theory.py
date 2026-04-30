"""
music_theory.py — scales, chords, and rhythm patterns for beat generation.
"""

from __future__ import annotations

import random
from typing import Optional

# ── Note name → semitone ──────────────────────────────────────────────────────

_NOTE_TO_SEMI: dict[str, int] = {
    "C": 0, "C#": 1, "DB": 1,
    "D": 2, "D#": 3, "EB": 3,
    "E": 4,
    "F": 5, "F#": 6, "GB": 6,
    "G": 7, "G#": 8, "AB": 8,
    "A": 9, "A#": 10, "BB": 10,
    "B": 11,
}

_SEMI_TO_NOTE: list[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# ── Scale intervals (semitones from root) ────────────────────────────────────

SCALES: dict[str, list[int]] = {
    "major":             [0, 2, 4, 5, 7, 9, 11],
    "minor":             [0, 2, 3, 5, 7, 8, 10],
    "pentatonic_major":  [0, 2, 4, 7, 9],
    "pentatonic_minor":  [0, 3, 5, 7, 10],
    "dorian":            [0, 2, 3, 5, 7, 9, 10],
    "phrygian":          [0, 1, 3, 5, 7, 8, 10],
    "blues":             [0, 3, 5, 6, 7, 10],
}

# ── Chord progressions per genre (scale degree indices, 0-based) ─────────────
# Each entry is a list of bars; each bar is a scale degree index.
# Degree 0 = root, 2 = third scale degree, 4 = fifth, 6 = seventh.

CHORD_PROGRESSIONS: dict[str, dict] = {
    "trap": {
        "scale": "pentatonic_minor",
        "progression": [0, 3, 2, 4],       # i - iv - III - v
        "chord_voicing": "power",
    },
    "uk drill": {
        "scale": "minor",
        "progression": [0, 5, 6, 5],        # i - VI - VII - VI
        "chord_voicing": "minor_triad",
    },
    "drill": {
        "scale": "minor",
        "progression": [0, 5, 6, 5],
        "chord_voicing": "minor_triad",
    },
    "house": {
        "scale": "minor",
        "progression": [0, 3, 5, 4],        # i - iv - VI - v
        "chord_voicing": "minor_triad",
    },
    "lo-fi": {
        "scale": "dorian",
        "progression": [0, 3, 4, 2],        # i - iv - v - III
        "chord_voicing": "seventh",
    },
    "lofi": {
        "scale": "dorian",
        "progression": [0, 3, 4, 2],
        "chord_voicing": "seventh",
    },
    "hip hop": {
        "scale": "minor",
        "progression": [0, 5, 3, 6],        # i - VI - iv - VII
        "chord_voicing": "minor_triad",
    },
    "boom bap": {
        "scale": "minor",
        "progression": [0, 5, 3, 4],
        "chord_voicing": "minor_triad",
    },
    "edm": {
        "scale": "minor",
        "progression": [0, 5, 3, 6],
        "chord_voicing": "minor_triad",
    },
    "reggaeton": {
        "scale": "minor",
        "progression": [0, 3, 5, 4],
        "chord_voicing": "minor_triad",
    },
    "afrobeat": {
        "scale": "pentatonic_major",
        "progression": [0, 2, 4, 2],
        "chord_voicing": "power",
    },
    "dancehall": {
        "scale": "minor",
        "progression": [0, 3, 5, 6],
        "chord_voicing": "minor_triad",
    },
}

# ── Drum patterns (16-step grid, 1 bar, 1=hit, 0=rest) ──────────────────────
# Each step is a 16th note. Steps 0,4,8,12 = beats 1,2,3,4.
# Velocity is per step (0 = no hit).

DRUM_PATTERNS: dict[str, dict[str, list[int]]] = {
    "trap": {
        # kick: beat 1, syncopated hits
        "kick":         [100, 0,  0,  0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  80, 0],
        # snare: beat 2 and 4
        "snare":        [0,   0,  0,  0,  100,0,  0,  0,  0,  0,  0,  0,  100,0,  0,  0],
        # 16th triplet hi-hats (approximated on 16-step grid)
        "hihat_closed": [90,  75, 90, 75, 90, 75, 90, 75, 90, 75, 90, 75, 90, 75, 90, 75],
        "hihat_open":   [0,   0,  0,  80, 0,  0,  0,  80, 0,  0,  0,  80, 0,  0,  0,  80],
        "clap":         [0,   0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  85, 0,  0,  0],
    },
    "uk drill": {
        "kick":         [100, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  0,  0,  85, 0,  0],
        "snare":        [0,   0,  0,  0,  100,0,  0,  80, 0,  0,  0,  0,  100,0,  80, 0],
        "hihat_closed": [80,  0,  85, 0,  80, 0,  85, 65, 80, 0,  85, 0,  80, 0,  85, 65],
        "hihat_open":   [0,   0,  0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0],
        "clap":         [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    },
    "drill": {
        "kick":         [100, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  0,  0,  85, 0,  0],
        "snare":        [0,   0,  0,  0,  100,0,  0,  80, 0,  0,  0,  0,  100,0,  80, 0],
        "hihat_closed": [80,  0,  85, 0,  80, 0,  85, 65, 80, 0,  85, 0,  80, 0,  85, 65],
        "hihat_open":   [0,   0,  0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0],
        "clap":         [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    },
    "house": {
        "kick":         [100, 0,  0,  0,  100,0,  0,  0,  100,0,  0,  0,  100,0,  0,  0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  0],
        "hihat_closed": [80,  0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0],
        "hihat_open":   [0,   0,  85, 0,  0,  0,  85, 0,  0,  0,  85, 0,  0,  0,  85, 0],
        "clap":         [0,   0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  85, 0,  0,  0],
    },
    "lo-fi": {
        "kick":         [100, 0,  0,  0,  0,  0,  0,  70, 0,  0,  0,  0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  70, 0,  90, 0,  0,  0],
        "hihat_closed": [70,  0,  75, 0,  70, 0,  75, 0,  70, 0,  75, 0,  70, 0,  75, 0],
        "hihat_open":   [0,   0,  0,  65, 0,  0,  0,  0,  0,  0,  0,  65, 0,  0,  0,  0],
        "clap":         [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    },
    "hip hop": {
        "kick":         [100, 0,  0,  0,  0,  0,  80, 0,  0,  90, 0,  0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  100,0,  0,  0,  0,  0,  0,  0,  100,0,  0,  75],
        "hihat_closed": [75,  0,  75, 0,  75, 0,  75, 0,  75, 0,  75, 0,  75, 0,  75, 0],
        "hihat_open":   [0,   0,  0,  80, 0,  0,  0,  0,  0,  0,  0,  80, 0,  0,  0,  0],
        "clap":         [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    },
    "boom bap": {
        "kick":         [100, 0,  0,  0,  0,  0,  0,  0,  80, 0,  0,  0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  100,0,  0,  0,  0,  0,  0,  0,  100,0,  0,  0],
        "hihat_closed": [80,  60, 80, 60, 80, 60, 80, 60, 80, 60, 80, 60, 80, 60, 80, 60],
        "hihat_open":   [0,   0,  0,  0,  0,  0,  0,  80, 0,  0,  0,  0,  0,  0,  0,  80],
        "clap":         [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    },
    "edm": {
        "kick":         [100, 0,  0,  0,  100,0,  0,  0,  100,0,  0,  0,  100,0,  0,  0],
        "snare":        [0,   0,  0,  0,  95, 0,  0,  0,  0,  0,  0,  0,  95, 0,  0,  0],
        "hihat_closed": [80,  80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80],
        "hihat_open":   [0,   0,  85, 0,  0,  0,  85, 0,  0,  0,  85, 0,  0,  0,  85, 0],
        "clap":         [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  0],
    },
    "reggaeton": {
        "kick":         [100, 0,  0,  0,  0,  0,  80, 0,  0,  0,  80, 0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  0],
        "hihat_closed": [80,  0,  80, 80, 80, 0,  80, 80, 80, 0,  80, 80, 80, 0,  80, 80],
        "hihat_open":   [0,   0,  0,  0,  0,  75, 0,  0,  0,  0,  0,  0,  0,  75, 0,  0],
        "clap":         [0,   0,  0,  75, 0,  0,  0,  75, 0,  0,  0,  75, 0,  0,  0,  75],
    },
    "afrobeat": {
        "kick":         [100, 0,  0,  80, 0,  0,  0,  0,  90, 0,  0,  0,  0,  80, 0,  0],
        "snare":        [0,   0,  0,  0,  85, 0,  0,  75, 0,  0,  0,  0,  85, 0,  0,  75],
        "hihat_closed": [80,  80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80],
        "hihat_open":   [0,   0,  0,  0,  0,  0,  75, 0,  0,  0,  0,  0,  0,  0,  75, 0],
        "clap":         [0,   0,  75, 0,  0,  0,  75, 0,  0,  0,  75, 0,  0,  0,  75, 0],
    },
}

# Standard GM drum note numbers
DRUM_NOTES: dict[str, int] = {
    "kick":         36,
    "snare":        38,
    "hihat_closed": 42,
    "hihat_open":   46,
    "clap":         39,
    "tom_high":     48,
    "tom_mid":      47,
    "tom_low":      45,
    "crash":        49,
    "ride":         51,
}

# ── Melody rhythm templates (16-step, 1=note position, 0=rest) ──────────────

MELODY_RHYTHMS: dict[str, list[list[int]]] = {
    "trap": [
        [1, 0, 0, 0,  1, 0, 0, 1,  0, 0, 1, 0,  0, 0, 0, 0],
        [1, 0, 0, 0,  0, 0, 1, 0,  0, 1, 0, 0,  1, 0, 0, 0],
    ],
    "uk drill": [
        [1, 0, 0, 0,  0, 0, 1, 0,  0, 0, 0, 1,  0, 0, 0, 0],
        [1, 0, 0, 1,  0, 0, 0, 0,  1, 0, 0, 0,  0, 1, 0, 0],
    ],
    "drill": [
        [1, 0, 0, 0,  0, 0, 1, 0,  0, 0, 0, 1,  0, 0, 0, 0],
        [1, 0, 0, 1,  0, 0, 0, 0,  1, 0, 0, 0,  0, 1, 0, 0],
    ],
    "house": [
        [1, 0, 0, 0,  1, 0, 1, 0,  1, 0, 0, 0,  1, 0, 1, 0],
        [0, 1, 0, 0,  0, 1, 0, 1,  0, 0, 1, 0,  0, 1, 0, 0],
    ],
    "lo-fi": [
        [1, 0, 0, 0,  0, 1, 0, 0,  0, 0, 1, 0,  0, 0, 0, 1],
        [1, 0, 0, 0,  1, 0, 0, 0,  0, 1, 0, 0,  1, 0, 0, 0],
    ],
    "hip hop": [
        [1, 0, 0, 0,  0, 1, 0, 0,  1, 0, 0, 1,  0, 0, 0, 0],
        [1, 0, 0, 1,  0, 0, 1, 0,  0, 0, 1, 0,  0, 1, 0, 0],
    ],
    "boom bap": [
        [1, 0, 0, 0,  0, 1, 0, 0,  1, 0, 0, 0,  0, 1, 0, 0],
        [1, 0, 0, 0,  1, 0, 0, 0,  0, 0, 1, 0,  0, 0, 1, 0],
    ],
    "edm": [
        [1, 0, 1, 0,  1, 0, 1, 0,  1, 0, 1, 0,  1, 0, 1, 0],
        [1, 0, 0, 1,  0, 1, 0, 0,  1, 0, 0, 1,  0, 1, 0, 0],
    ],
    "reggaeton": [
        [1, 0, 0, 0,  1, 0, 1, 0,  0, 0, 1, 0,  1, 0, 0, 0],
        [1, 0, 1, 0,  0, 0, 0, 1,  1, 0, 0, 0,  1, 0, 1, 0],
    ],
    "afrobeat": [
        [1, 0, 1, 0,  0, 1, 0, 1,  1, 0, 0, 1,  0, 1, 0, 0],
        [1, 0, 0, 1,  1, 0, 1, 0,  0, 1, 0, 0,  1, 0, 1, 0],
    ],
}

# ── BPM ranges per genre ─────────────────────────────────────────────────────

GENRE_BPM: dict[str, tuple[int, int]] = {
    "trap":      (130, 160),
    "uk drill":  (140, 145),
    "drill":     (140, 145),
    "house":     (120, 130),
    "lo-fi":     (70,  90),
    "lofi":      (70,  90),
    "hip hop":   (85,  100),
    "boom bap":  (85,  100),
    "edm":       (128, 135),
    "reggaeton": (92,  98),
    "afrobeat":  (100, 115),
    "dancehall": (100, 110),
}

# ── Core functions ───────────────────────────────────────────────────────────

def parse_root(root: str) -> int:
    """Convert note name to semitone (0=C, 1=C#, ...)."""
    key = root.upper().replace("B", "B").strip()
    # Handle flats spelled as 'b' suffix
    if len(key) == 2 and key[1] == "B" and key[0] != "B":
        flat_map = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}
        key = flat_map.get(key, key)
    result = _NOTE_TO_SEMI.get(key)
    if result is None:
        raise ValueError(f"Unknown root note: {root!r}")
    return result


def scale_midi_notes(root: str, scale_name: str, octave: int = 4, num_octaves: int = 2) -> list[int]:
    """Return all MIDI note numbers for a scale across num_octaves."""
    root_semi = parse_root(root)
    intervals = SCALES.get(scale_name, SCALES["minor"])
    base = (octave + 1) * 12 + root_semi
    notes = []
    for o in range(num_octaves):
        for interval in intervals:
            n = base + o * 12 + interval
            if 0 <= n <= 127:
                notes.append(n)
    return notes


def chord_midi_notes(root: str, scale_name: str, degree: int, octave: int = 3, voicing: str = "minor_triad") -> list[int]:
    """Return MIDI note numbers for a chord built on scale degree (0-based)."""
    root_semi = parse_root(root)
    intervals = SCALES.get(scale_name, SCALES["minor"])

    # Get the degree's root semitone
    degree_idx = degree % len(intervals)
    chord_root_offset = intervals[degree_idx]
    chord_root_midi = (octave + 1) * 12 + root_semi + chord_root_offset

    if voicing == "power":
        # Root + fifth
        return [chord_root_midi, chord_root_midi + 7]

    # Build triad from scale degrees
    chord_intervals = []
    for step in [0, 2, 4]:
        idx = (degree_idx + step) % len(intervals)
        offset = intervals[idx]
        if idx < degree_idx + step:
            offset += 12  # wrap around
        chord_intervals.append(offset - intervals[degree_idx])

    if voicing == "seventh":
        idx = (degree_idx + 6) % len(intervals)
        offset = intervals[idx]
        if idx < degree_idx + 6:
            offset += 12
        chord_intervals.append(offset - intervals[degree_idx])

    return [chord_root_midi + i for i in chord_intervals if 0 <= chord_root_midi + i <= 127]


def chord_name(root: str, scale_name: str, degree: int) -> str:
    """Return a human-readable chord name."""
    root_semi = parse_root(root)
    intervals = SCALES.get(scale_name, SCALES["minor"])
    degree_idx = degree % len(intervals)
    chord_root_semi = (root_semi + intervals[degree_idx]) % 12
    note = _SEMI_TO_NOTE[chord_root_semi]
    # Determine major/minor quality from scale
    third_step = intervals[(degree_idx + 2) % len(intervals)] - intervals[degree_idx]
    if third_step < 0:
        third_step += 12
    quality = "m" if third_step == 3 else ""
    return f"{note}{quality}"


def get_genre_defaults(genre: str) -> dict:
    """Return default scale and progression for a genre."""
    genre_lower = genre.lower()
    prog_data = CHORD_PROGRESSIONS.get(genre_lower, CHORD_PROGRESSIONS["hip hop"])
    bpm_range = GENRE_BPM.get(genre_lower, (120, 140))
    return {
        "scale": prog_data["scale"],
        "progression": prog_data["progression"],
        "chord_voicing": prog_data["chord_voicing"],
        "bpm_default": (bpm_range[0] + bpm_range[1]) // 2,
    }


def generate_drum_notes(genre: str, bars: int, humanize: bool = True) -> list[dict]:
    """Generate drum note list for given genre and bar count."""
    genre_lower = genre.lower()
    pattern = DRUM_PATTERNS.get(genre_lower, DRUM_PATTERNS["hip hop"])
    notes = []

    steps_per_bar = 16
    step_duration = 0.25  # 1/16th note in beats

    for bar in range(bars):
        for drum_name, step_velocities in pattern.items():
            midi_note = DRUM_NOTES.get(drum_name)
            if midi_note is None:
                continue
            for step, vel in enumerate(step_velocities):
                if vel == 0:
                    continue
                beat_time = bar * 4.0 + step * step_duration
                actual_vel = vel
                if humanize:
                    actual_vel = max(1, min(127, vel + random.randint(-8, 8)))
                notes.append({
                    "note": midi_note,
                    "velocity": actual_vel,
                    "duration": step_duration * 0.9,
                    "time": beat_time,
                    "channel": 9,  # GM drums channel (0-indexed = channel 10)
                    "track": "drums",
                })

    return notes


def generate_bass_notes(
    root: str,
    scale_name: str,
    progression: list[int],
    bars: int,
    octave: int = 2,
    style: str = "root",
) -> list[dict]:
    """Generate bass/808 notes following chord progression."""
    intervals = SCALES.get(scale_name, SCALES["minor"])
    notes = []
    bars_per_chord = max(1, bars // len(progression))
    beat = 0.0

    for bar_idx in range(bars):
        chord_idx = (bar_idx // bars_per_chord) % len(progression)
        degree = progression[chord_idx]
        degree_idx = degree % len(intervals)
        root_semi = parse_root(root)
        bass_root = (octave + 1) * 12 + root_semi + intervals[degree_idx]

        if style == "root":
            # Whole note bass hit per bar with slide feel
            notes.append({
                "note": bass_root,
                "velocity": 100,
                "duration": 3.5,
                "time": beat,
                "channel": 1,
                "track": "bass",
            })
        elif style == "walking":
            # Two hits per bar
            notes.append({
                "note": bass_root,
                "velocity": 95,
                "duration": 1.8,
                "time": beat,
                "channel": 1,
                "track": "bass",
            })
            fifth_idx = (degree_idx + 4) % len(intervals)
            bass_fifth = (octave + 1) * 12 + root_semi + intervals[fifth_idx]
            notes.append({
                "note": bass_fifth,
                "velocity": 85,
                "duration": 1.8,
                "time": beat + 2.0,
                "channel": 1,
                "track": "bass",
            })

        beat += 4.0

    return notes


def generate_melody_notes(
    root: str,
    scale_name: str,
    progression: list[int],
    bars: int,
    octave: int = 4,
    humanize: bool = True,
) -> list[dict]:
    """Generate a melody following the chord progression and genre rhythm."""
    scale_notes_list = scale_midi_notes(root, scale_name, octave=octave, num_octaves=2)
    intervals = SCALES.get(scale_name, SCALES["minor"])
    notes = []
    step_dur = 0.25  # 1/16th note
    bars_per_chord = max(1, bars // len(progression))

    # Track current position in scale for smooth voice leading
    current_note_idx = len(scale_notes_list) // 4

    for bar_idx in range(bars):
        chord_idx = (bar_idx // bars_per_chord) % len(progression)
        degree = progression[chord_idx]
        degree_idx = degree % len(intervals)
        root_semi = parse_root(root)
        chord_root_midi = (octave + 1) * 12 + root_semi + intervals[degree_idx]

        # Find chord tones within scale_notes_list
        chord_tones = [n for n in scale_notes_list if (n - chord_root_midi) % 12 in [0, 3, 4, 7]]
        if not chord_tones:
            chord_tones = scale_notes_list

        # Pick a rhythm template (alternate bars)
        rhythm_key = "hip hop"
        for k in MELODY_RHYTHMS:
            if k in ["trap", "uk drill", "drill", "house", "lo-fi", "hip hop", "boom bap", "edm", "reggaeton", "afrobeat"]:
                rhythm_key = k
                break

        rhythms = MELODY_RHYTHMS.get(rhythm_key, MELODY_RHYTHMS["hip hop"])
        rhythm = rhythms[bar_idx % len(rhythms)]

        for step, hit in enumerate(rhythm):
            if hit == 0:
                continue
            beat_time = bar_idx * 4.0 + step * step_dur

            # 70% chance to use chord tone, 30% passing tone
            if random.random() < 0.7 and chord_tones:
                # Move to nearest chord tone
                target = min(chord_tones, key=lambda n: abs(n - scale_notes_list[current_note_idx]))
                current_note_idx = scale_notes_list.index(target) if target in scale_notes_list else current_note_idx
            else:
                # Step-wise motion within scale
                direction = random.choice([-1, 0, 0, 1])
                current_note_idx = max(0, min(len(scale_notes_list) - 1, current_note_idx + direction))

            midi_note = scale_notes_list[current_note_idx]
            vel = 85 if random.random() > 0.3 else 70
            if humanize:
                vel = max(1, min(127, vel + random.randint(-10, 10)))

            # Duration: usually 1-2 steps
            dur_steps = random.choices([1, 2, 3, 4], weights=[0.4, 0.35, 0.15, 0.1])[0]
            notes.append({
                "note": midi_note,
                "velocity": vel,
                "duration": dur_steps * step_dur * 0.9,
                "time": beat_time,
                "channel": 2,
                "track": "melody",
            })

    return notes


def generate_chord_notes(
    root: str,
    scale_name: str,
    progression: list[int],
    bars: int,
    voicing: str = "minor_triad",
    octave: int = 3,
) -> list[dict]:
    """Generate sustained chord pad notes."""
    notes = []
    bars_per_chord = max(1, bars // len(progression))

    for bar_idx in range(bars):
        chord_idx = (bar_idx // bars_per_chord) % len(progression)
        degree = progression[chord_idx]
        chord = chord_midi_notes(root, scale_name, degree, octave=octave, voicing=voicing)

        beat_time = bar_idx * 4.0
        for midi_note in chord:
            notes.append({
                "note": midi_note,
                "velocity": 60,
                "duration": 3.8,
                "time": beat_time,
                "channel": 3,
                "track": "chords",
            })

    return notes
