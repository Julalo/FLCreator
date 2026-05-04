"""
music_theory.py — scales, chords, drum patterns, and genre knowledge.
"""

from __future__ import annotations

import random
from typing import Optional

# ── Note name → semitone ─────────────────────────────────────────────────────

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

# ── Scales ───────────────────────────────────────────────────────────────────

SCALES: dict[str, list[int]] = {
    "major":            [0, 2, 4, 5, 7, 9, 11],
    "minor":            [0, 2, 3, 5, 7, 8, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "blues":            [0, 3, 5, 6, 7, 10],
    "harmonic_minor":   [0, 2, 3, 5, 7, 8, 11],
}

# ── Chord progressions per genre ─────────────────────────────────────────────

CHORD_PROGRESSIONS: dict[str, dict] = {
    "trap": {
        "scale": "pentatonic_minor",
        "progression": [0, 3, 2, 4],
        "chord_voicing": "power",
    },
    "uk drill": {
        "scale": "minor",
        "progression": [0, 5, 6, 5],
        "chord_voicing": "minor_triad",
    },
    "drill": {
        "scale": "minor",
        "progression": [0, 5, 6, 5],
        "chord_voicing": "minor_triad",
    },
    "house": {
        "scale": "minor",
        "progression": [0, 3, 5, 4],
        "chord_voicing": "minor_triad",
    },
    "lo-fi": {
        "scale": "dorian",
        "progression": [0, 3, 4, 2],
        "chord_voicing": "seventh",
    },
    "lofi": {
        "scale": "dorian",
        "progression": [0, 3, 4, 2],
        "chord_voicing": "seventh",
    },
    "hip hop": {
        "scale": "minor",
        "progression": [0, 5, 3, 6],
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
    # Reggaeton: i - VII - III - VI in minor — piano-friendly, bright
    "reggaeton": {
        "scale": "minor",
        "progression": [0, 6, 2, 5],
        "chord_voicing": "minor_triad",
    },
    # Dembow (same as reggaeton but slightly darker)
    "dembow": {
        "scale": "minor",
        "progression": [0, 6, 2, 5],
        "chord_voicing": "minor_triad",
    },
    "afrobeat": {
        "scale": "pentatonic_major",
        "progression": [0, 2, 4, 2],
        "chord_voicing": "power",
    },
    # Dancehall: major feel, uplifting
    "dancehall": {
        "scale": "major",
        "progression": [0, 3, 4, 3],
        "chord_voicing": "minor_triad",
    },
    # R&B: lush seventh chords
    "r&b": {
        "scale": "dorian",
        "progression": [0, 3, 2, 5],
        "chord_voicing": "seventh",
    },
    "rnb": {
        "scale": "dorian",
        "progression": [0, 3, 2, 5],
        "chord_voicing": "seventh",
    },
    # Bachata: minor with romantic feel
    "bachata": {
        "scale": "minor",
        "progression": [0, 5, 3, 4],
        "chord_voicing": "minor_triad",
    },
    # Cumbia: major, bright and danceable
    "cumbia": {
        "scale": "major",
        "progression": [0, 4, 3, 4],
        "chord_voicing": "minor_triad",
    },
    # Jersey club: minor, energetic
    "jersey club": {
        "scale": "minor",
        "progression": [0, 5, 6, 3],
        "chord_voicing": "minor_triad",
    },
    # Amapiano: dorian, jazzy
    "amapiano": {
        "scale": "dorian",
        "progression": [0, 3, 4, 5],
        "chord_voicing": "seventh",
    },
}

# ── Drum patterns (16-step, 1 bar, velocity or 0=rest) ──────────────────────
# Steps 0,4,8,12 = beats 1,2,3,4. Each step = 1/16th note.

DRUM_PATTERNS: dict[str, dict[str, list[int]]] = {
    "trap": {
        # Kick on 1 with syncopated ghost kicks
        "kick":         [100, 0,  0,  0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  80, 0],
        # Snare on 2 and 4
        "snare":        [0,   0,  0,  0,  100,0,  0,  0,  0,  0,  0,  0,  100,0,  0,  0],
        # Triplet hi-hats (approximated on 16-step)
        "hihat_closed": [90,  75, 90, 75, 90, 75, 90, 75, 90, 75, 90, 75, 90, 75, 90, 75],
        "hihat_open":   [0,   0,  0,  80, 0,  0,  0,  80, 0,  0,  0,  80, 0,  0,  0,  80],
        "clap":         [0,   0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  85, 0,  0,  0],
    },
    "uk drill": {
        # UK Drill: kicks on 1 and syncopated 3, snare on 2/4 with rolls
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
        # 4-on-the-floor kick, off-beat open hats
        "kick":         [100, 0,  0,  0,  100,0,  0,  0,  100,0,  0,  0,  100,0,  0,  0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  0],
        "hihat_closed": [80,  0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0],
        "hihat_open":   [0,   0,  85, 0,  0,  0,  85, 0,  0,  0,  85, 0,  0,  0,  85, 0],
        "clap":         [0,   0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  85, 0,  0,  0],
    },
    "lo-fi": {
        # Swung, loose feel — humanize heavily
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
    # ── REGGAETON / DEMBOW ───────────────────────────────────────────────────
    # The dembow rhythm is THE defining element of reggaeton.
    # Kick: beats 1 and 3 (steps 0, 8)
    # Rimshot: beat 2 (step 4), AND-of-3 (step 10), beat 4 (step 12)
    #          The step-10 rimshot is the "dembow shot" — never remove it.
    # Hi-hats: straight 16ths, no swung feel
    "reggaeton": {
        "kick":         [100, 0,  0,  0,  0,  0,  0,  0,  100,0,  0,  0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  85, 0,  90, 0,  0,  0],
        "hihat_closed": [75,  75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75],
        "hihat_open":   [0,   0,  0,  0,  0,  0,  0,  70, 0,  0,  0,  0,  0,  0,  0,  70],
        "clap":         [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    },
    "dembow": {
        "kick":         [100, 0,  0,  0,  0,  0,  0,  0,  100,0,  0,  0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  85, 0,  90, 0,  0,  0],
        "hihat_closed": [75,  75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75, 75],
        "hihat_open":   [0,   0,  0,  0,  0,  0,  0,  70, 0,  0,  0,  0,  0,  0,  0,  70],
        "clap":         [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    },
    # ── AFROBEAT ─────────────────────────────────────────────────────────────
    # Polyrhythmic — kick and snare on offbeats, 16th hats throughout
    "afrobeat": {
        "kick":         [100, 0,  0,  80, 0,  0,  0,  0,  90, 0,  0,  0,  0,  80, 0,  0],
        "snare":        [0,   0,  0,  0,  85, 0,  0,  75, 0,  0,  0,  0,  85, 0,  0,  75],
        "hihat_closed": [80,  80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80],
        "hihat_open":   [0,   0,  0,  0,  0,  0,  75, 0,  0,  0,  0,  0,  0,  0,  75, 0],
        "clap":         [0,   0,  75, 0,  0,  0,  75, 0,  0,  0,  75, 0,  0,  0,  75, 0],
    },
    # ── DANCEHALL ────────────────────────────────────────────────────────────
    # "One drop" feel — kick hits on beat 3 only, snare on 2 and 4
    "dancehall": {
        "kick":         [0,   0,  0,  0,  0,  0,  0,  0,  100,0,  0,  0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  75],
        "hihat_closed": [80,  0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0,  80, 0],
        "hihat_open":   [0,   0,  0,  85, 0,  0,  0,  85, 0,  0,  0,  85, 0,  0,  0,  85],
        "clap":         [0,   0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  85, 0,  0,  0],
    },
    # ── R&B ──────────────────────────────────────────────────────────────────
    # Slow groove, kick on 1 and 3, snare ghost notes, sparse hats
    "r&b": {
        "kick":         [100, 0,  0,  0,  0,  0,  70, 0,  100,0,  0,  0,  0,  60, 0,  0],
        "snare":        [0,   0,  0,  0,  95, 0,  0,  0,  0,  40, 0,  0,  95, 0,  0,  40],
        "hihat_closed": [65,  0,  65, 0,  65, 0,  65, 0,  65, 0,  65, 0,  65, 0,  65, 0],
        "hihat_open":   [0,   0,  0,  70, 0,  0,  0,  0,  0,  0,  0,  70, 0,  0,  0,  0],
        "clap":         [0,   0,  0,  0,  75, 0,  0,  0,  0,  0,  0,  0,  75, 0,  0,  0],
    },
    "rnb": {
        "kick":         [100, 0,  0,  0,  0,  0,  70, 0,  100,0,  0,  0,  0,  60, 0,  0],
        "snare":        [0,   0,  0,  0,  95, 0,  0,  0,  0,  40, 0,  0,  95, 0,  0,  40],
        "hihat_closed": [65,  0,  65, 0,  65, 0,  65, 0,  65, 0,  65, 0,  65, 0,  65, 0],
        "hihat_open":   [0,   0,  0,  70, 0,  0,  0,  0,  0,  0,  0,  70, 0,  0,  0,  0],
        "clap":         [0,   0,  0,  0,  75, 0,  0,  0,  0,  0,  0,  0,  75, 0,  0,  0],
    },
    # ── BACHATA ──────────────────────────────────────────────────────────────
    # 4-beat rhythm with a rest on beat 4 (the "bache") + maracas feel
    "bachata": {
        "kick":         [100, 0,  0,  0,  80, 0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  0],
        "hihat_closed": [85,  0,  85, 0,  85, 0,  85, 0,  85, 0,  85, 0,  0,  0,  0,  0],
        "hihat_open":   [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  80, 0],
        "clap":         [0,   70, 0,  70, 0,  70, 0,  70, 0,  70, 0,  70, 0,  70, 0,  0],
    },
    # ── CUMBIA ───────────────────────────────────────────────────────────────
    # Syncopated, caja drum feel + maracas
    "cumbia": {
        "kick":         [100, 0,  0,  0,  0,  0,  80, 0,  0,  0,  100,0,  0,  0,  0,  0],
        "snare":        [0,   0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  85, 0,  0,  75],
        "hihat_closed": [80,  80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80],
        "hihat_open":   [0,   0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
        "clap":         [0,   75, 0,  75, 0,  75, 0,  75, 0,  75, 0,  75, 0,  75, 0,  75],
    },
    # ── JERSEY CLUB ──────────────────────────────────────────────────────────
    # Rapid kick pattern, stuttering snare, 140 BPM feel
    "jersey club": {
        "kick":         [100, 0,  100,0,  0,  0,  100,0,  100,0,  0,  0,  100,0,  100,0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  90, 0,  0,  0,  0,  90, 0,  0,  90],
        "hihat_closed": [80,  80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80],
        "hihat_open":   [0,   0,  0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  85, 0,  0],
        "clap":         [0,   0,  0,  0,  85, 0,  0,  0,  0,  0,  0,  0,  85, 0,  0,  0],
    },
    # ── AMAPIANO ─────────────────────────────────────────────────────────────
    # Log drum is the signature — modeled as hi-hat + snare combo, 112 BPM
    "amapiano": {
        "kick":         [100, 0,  0,  0,  0,  0,  85, 0,  100,0,  0,  0,  0,  0,  80, 0],
        "snare":        [0,   0,  0,  0,  90, 0,  0,  0,  0,  0,  0,  0,  90, 0,  0,  0],
        "hihat_closed": [70,  70, 85, 70, 70, 70, 85, 70, 70, 70, 85, 70, 70, 70, 85, 70],
        "hihat_open":   [0,   0,  0,  0,  0,  80, 0,  0,  0,  0,  0,  0,  0,  80, 0,  0],
        "clap":         [0,   0,  0,  0,  80, 0,  0,  80, 0,  0,  0,  0,  80, 0,  0,  80],
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

# ── Genre-specific instrument knowledge ─────────────────────────────────────
# What instruments, sounds, and production elements define each genre.
# Used by the server to guide plugin recommendations and channel setup.

GENRE_INSTRUMENTS: dict[str, dict] = {
    "reggaeton": {
        "drums": [
            "rimshot (snare processed to cut through mix)",
            "kick (punchy, short — NOT a boomy trap kick)",
            "hi-hat (straight 16ths, no swing)",
            "congas or bongos (adds perreo texture)",
            "rim (timbal-style for variation)",
        ],
        "bass": [
            "808 bass (short attack, medium sustain — not the sliding trap 808)",
            "synth bass (Serum or Massive — punchy sub)",
        ],
        "melody": [
            "acoustic piano or electric piano (the #1 reggaeton melodic sound)",
            "synth pluck (Nexus, Serum)",
            "brass stabs (horns on chord hits)",
            "flute sample",
        ],
        "chords": [
            "piano chords (tight voicing, no sustain pedal feel)",
            "organ pads",
        ],
        "fx": ["vinyl crackle (optional)", "reggaeton vocal samples", "whistle hits"],
        "signature": "The dembow rimshot is sacred — it goes on beat 2, and-of-3, and beat 4. Remove it and it stops being reggaeton.",
        "key_plugins": ["Nexus 3 (has reggaeton kits)", "Serum", "Kontakt", "Native Instruments Una Corda (piano)"],
        "avoid": ["Sliding 808 glide (that's trap)", "Triplet hi-hats (that's trap)", "Dark minor pads without piano"],
    },
    "trap": {
        "drums": [
            "808 bass (pitched, long sustain with portamento/glide)",
            "kick (boomy, sub-heavy)",
            "snare (clap-layered, sharp attack)",
            "hi-hat triplets (1/8T and 1/16T rolls — the trap fingerprint)",
            "open hi-hat (on the 'e' of beats)",
        ],
        "bass": [
            "808 (pitched chromatically to match the melody — this IS the bass in trap)",
        ],
        "melody": [
            "Serum / Vital dark lead",
            "Kontakt piano (pitched down for that dark feel)",
            "guitar sample (picked or strummed)",
            "strings (often reversed or heavily reverbed)",
            "flute pluck (popular in modern trap)",
        ],
        "chords": [
            "dark pad (Serum, Omnisphere)",
            "Rhodes sample",
        ],
        "signature": "The 808 is the bass AND the melody anchor. Pitch it to every chord root. The hi-hat triplet rolls define the energy.",
        "key_plugins": ["Serum", "Kontakt", "Omnisphere", "Vital", "3xOsc (for 808 layering)"],
        "avoid": ["Straight 16th hi-hats (sounds too house)", "Short 808 (loses the trap feel)"],
    },
    "uk drill": {
        "drums": [
            "kick (slightly filtered, not as boomy as US trap)",
            "snare (tight, with rolls on the and-of-2 and and-of-4)",
            "hi-hat (syncopated, with open hats on offbeats)",
            "no clap (UK drill rarely uses claps)",
        ],
        "bass": [
            "sliding 808 (even more portamento than US trap)",
            "piano bass doubling the 808 melody",
        ],
        "melody": [
            "dark piano (heavily reverbed)",
            "strings (minor, cinematic)",
            "guitar (minor, atmospheric)",
            "Serum dark lead",
        ],
        "chords": ["dark pad", "string ensemble"],
        "signature": "C minor and F# minor are the go-to keys. The 808 slides between notes. Melody is cinematic and dark.",
        "key_plugins": ["Serum", "Kontakt", "Vital", "Spire"],
        "avoid": ["Major scales", "Bright sounds", "House-style hi-hats"],
    },
    "house": {
        "drums": [
            "kick (4-on-the-floor — mandatory, punchy with sub)",
            "clap or snare on beats 2 and 4",
            "open hi-hat on off-beats (the 'and' between kicks)",
            "shaker or tambourine (adds groove)",
            "rimshot ghost notes",
        ],
        "bass": [
            "bass line (syncopated, following the chord root with fills)",
            "sub bass (sine wave or 3xOsc)",
        ],
        "melody": [
            "chord stabs (Rhodes, Juno-style — the house signature)",
            "piano hook",
            "vocal chop",
            "synth lead (Sylenth1, Serum)",
        ],
        "chords": [
            "chord stabs (tight, off-beat)",
            "pad (slow attack, long release)",
        ],
        "signature": "The 4-on-the-floor kick never stops. Off-beat open hi-hat is as important as the kick. Chord stabs are everything.",
        "key_plugins": ["Sylenth1", "Serum", "Spire", "Juno-106 sample pack", "Kontakt"],
        "avoid": ["Swung hats (that's hip hop)", "Missing the off-beat open hat"],
    },
    "lo-fi": {
        "drums": [
            "MPC 60 / SP-404 drum samples (the lo-fi drum kit sound)",
            "kick (muffled, vintage)",
            "snare (with vinyl crackle baked in)",
            "hi-hat (swung, not straight — this is critical for lo-fi feel)",
            "rim",
        ],
        "bass": [
            "upright bass sample",
            "jazz electric bass",
            "sub sine (minimal)",
        ],
        "melody": [
            "Rhodes electric piano (the #1 lo-fi sound)",
            "Wurlitzer",
            "jazz guitar sample",
            "flute sample",
            "vibraphone",
        ],
        "chords": [
            "Rhodes or Wurlitzer jazz chords (seventh, ninth chords)",
            "guitar chords (strummed, slightly detuned)",
        ],
        "fx": ["vinyl crackle (always)", "tape wow/flutter", "lofi filter on mix bus"],
        "signature": "Swing the hi-hats. Everything should feel slightly imperfect and warm. Vinyl crackle is not optional.",
        "key_plugins": ["Kontakt (Lo-Fi Glow, Cassette Dreams)", "Vital", "Arturia Wurli V", "Sample packs (SP-404 kits)"],
        "avoid": ["Straight hi-hats", "Clean digital sounds", "Hard-clipping kick"],
    },
    "dancehall": {
        "drums": [
            "one-drop kick (hits ONLY on beat 3 — this is the one-drop)",
            "snare on beats 2 and 4",
            "open hi-hat (constant off-beat feel)",
            "rim or sidestick",
            "percussion (shaker, cowbell)",
        ],
        "bass": [
            "riddim bass (synthesized, follows root notes)",
            "sub bass (heavy)",
        ],
        "melody": [
            "synth lead (Nexus, Serum — bright and uplifting)",
            "horn stabs",
            "reggae guitar skank (choppy rhythm guitar on off-beats)",
            "piano",
        ],
        "chords": ["organ", "piano chords (bright, major)"],
        "signature": "The one-drop: kick ONLY on beat 3. This is what separates dancehall from everything else. Major key, bright feel.",
        "key_plugins": ["Nexus 3", "Serum", "Kontakt"],
        "avoid": ["4-on-the-floor kick (that's house)", "Minor key darkness (that's drill)"],
    },
    "afrobeat": {
        "drums": [
            "talking drum or conga (polyrhythmic — the backbone)",
            "kick (syncopated, not on beat 1 necessarily)",
            "snare (off-beat, crossing the groove)",
            "shaker (16th notes throughout)",
            "cowbell",
            "clap (syncopated)",
        ],
        "bass": [
            "funk bass (melodic, following the groove)",
            "electric bass (real or sampled)",
        ],
        "melody": [
            "guitar (rhythmic riff, often pentatonic)",
            "mbira / kalimba sound",
            "trumpet or tenor sax",
            "piano",
        ],
        "chords": ["horn section", "guitar chord stabs (off-beat)"],
        "signature": "Polyrhythm is the point — bass, guitar, and percussion are all on different grids. Major/pentatonic key, joyful feel.",
        "key_plugins": ["Kontakt (world instruments)", "Serum", "Sample packs (African percussion)"],
        "avoid": ["Straight 4/4 feel", "Dark minor chords"],
    },
    "hip hop": {
        "drums": [
            "kick (punchy, can be boomy or tight depending on sub-genre)",
            "snare (crisp, sometimes layered with clap)",
            "hi-hat (8th notes or swung 16ths)",
            "open hi-hat (one per bar, creates breathing)",
        ],
        "bass": [
            "808 or sub bass",
            "sample-based bass (chopped from soul/jazz records)",
        ],
        "melody": [
            "sample chop (the classic method — soul, jazz, funk samples)",
            "Rhodes or piano",
            "guitar",
            "synth lead",
        ],
        "chords": ["sample chop", "Rhodes pad", "choir sample"],
        "signature": "Sample-based workflow is traditional. Swing the drums 5-15%. The snare should feel like it's pushing you forward.",
        "key_plugins": ["Kontakt", "Serum", "3xOsc", "MPC sample packs"],
        "avoid": ["Straight (unswung) hi-hats for boom bap feel"],
    },
    "r&b": {
        "drums": [
            "kick (warm, not aggressive — sometimes sidechained softly)",
            "snare (ghost notes are key — snare on 2/4 plus many ghosts)",
            "hi-hat (sparse, 8th or 16th note feel with ghost hits)",
            "rim",
        ],
        "bass": [
            "electric bass (melodic lines, not just roots)",
            "808 (in modern R&B)",
            "synthesized bass (Serum, Omnisphere)",
        ],
        "melody": [
            "Rhodes or Fender Rhodes (the R&B sound)",
            "strings (lush, real or sampled)",
            "guitar (clean or lightly overdriven)",
            "synth pad (Omnisphere, Serum)",
            "vocal harmony sample",
        ],
        "chords": [
            "Rhodes seventh chords",
            "string pad",
            "choir (lush, layered)",
        ],
        "signature": "Groove and pocket matter more than complexity. Ghost notes on snare, Rhodes chords, and soul-inspired bass lines.",
        "key_plugins": ["Omnisphere", "Kontakt (Rhodes)", "Serum", "Arturia Wurli V"],
        "avoid": ["Aggressive drums", "Harsh synth tones", "Straight mechanical feel"],
    },
    "bachata": {
        "drums": [
            "bongo (the heartbeat of bachata — 3 hits + silence pattern)",
            "güira (metal scraper — constant 16th note texture)",
            "conga (bass and open tone alternating)",
            "kick (minimal, mostly on beat 1)",
            "snare (light, on beat 4)",
        ],
        "bass": [
            "electric bass (melodic, follows chord roots with fills)",
            "bass guitar sample",
        ],
        "melody": [
            "guitar (lead melody — the defining bachata sound)",
            "requinto (high guitar melody)",
            "piano (optional)",
            "flute (optional)",
        ],
        "chords": ["rhythm guitar (chord strumming)", "piano chords"],
        "signature": "The guitar IS the melody. Bongo pattern has a built-in 'rest' on beat 4 that creates the bachata feel.",
        "key_plugins": ["Kontakt (guitar samples)", "Sample packs (Latin percussion)", "Real guitar recording preferred"],
        "avoid": ["Electronic drums (kills the organic feel)", "Bright synth leads"],
    },
    "boom bap": {
        "drums": [
            "kick (round, boomy — SP-1200 or MPC 60 character)",
            "snare (cracking, sharp — often layered)",
            "hi-hat (alternating 8th notes with swing — the boom bap signature)",
            "open hi-hat (sparse, on the and-of-2 or and-of-4)",
        ],
        "bass": [
            "sample-based bass (chopped from jazz/soul records)",
            "upright bass sample",
        ],
        "melody": [
            "jazz or soul sample (the entire melody is often a chop)",
            "piano",
            "horn sample",
        ],
        "chords": ["sample chop", "Rhodes"],
        "signature": "Sample-based with heavy swing. The snare is the most important element — it should crack. No modern trap elements.",
        "key_plugins": ["Kontakt", "SP-1200 sample pack", "MPC sample pack"],
        "avoid": ["808 bass (too trap)", "Triplet hi-hats", "Dark synth pads"],
    },
    "edm": {
        "drums": [
            "kick (long sub tail, high-pass the rest of the mix when it hits)",
            "clap/snare (layered, punchy — on 2 and 4)",
            "hi-hat (straight 16ths or 8ths)",
            "crash (on every 16th bar to mark sections)",
        ],
        "bass": [
            "supersaw bass (Serum — detuned and filtered)",
            "pluck bass (on the root note)",
            "sub bass (layered under the lead)",
        ],
        "melody": [
            "supersaw lead (Serum, Sylenth1 — the EDM lead sound)",
            "arpeggiated synth",
            "pluck (the drop melody)",
        ],
        "chords": [
            "supersaw pad (massive detuned chords)",
            "stab synth (tight chord hits)",
        ],
        "signature": "The drop is everything. Build 16 bars, strip everything, then drop with the main lead + sidechain pumping kick.",
        "key_plugins": ["Serum", "Sylenth1", "Nexus", "Spire"],
        "avoid": ["Swung hats", "Organic sounds without heavy processing"],
    },
    "amapiano": {
        "drums": [
            "log drum (the amapiano signature — usually a short synth hit tuned to the key)",
            "kick (deep, sub-heavy)",
            "snare (medium, groovy)",
            "hi-hat (swung 16th feel)",
            "shaker",
        ],
        "bass": [
            "piano bass (left-hand piano walking the roots)",
            "deep synth bass (sub-focused)",
        ],
        "melody": [
            "grand piano (bright, chord-based runs)",
            "flute (melodic lines)",
            "strings",
            "synth pad",
        ],
        "chords": [
            "grand piano (right-hand chord stabs, jazzy voicings)",
            "pad synth",
        ],
        "signature": "The log drum is the identifier — sample a wooden hit, tune it to the key, sequence it rhythmically. Piano is always present.",
        "key_plugins": ["Kontakt (piano samples)", "Spire", "Sample packs (log drum kits)"],
        "avoid": ["Generic trap drums", "Ignoring the log drum"],
    },
}

# ── Melody rhythm templates (16-step, 1=note, 0=rest) ───────────────────────

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
    # Reggaeton melody: syncopated, hits on off-beats to contrast the straight hats
    "reggaeton": [
        [1, 0, 0, 1,  0, 0, 1, 0,  0, 1, 0, 0,  1, 0, 0, 0],
        [1, 0, 1, 0,  0, 1, 0, 0,  1, 0, 0, 1,  0, 0, 1, 0],
    ],
    "dembow": [
        [1, 0, 0, 1,  0, 0, 1, 0,  0, 1, 0, 0,  1, 0, 0, 0],
        [1, 0, 1, 0,  0, 1, 0, 0,  1, 0, 0, 1,  0, 0, 1, 0],
    ],
    "afrobeat": [
        [1, 0, 1, 0,  0, 1, 0, 1,  1, 0, 0, 1,  0, 1, 0, 0],
        [1, 0, 0, 1,  1, 0, 1, 0,  0, 1, 0, 0,  1, 0, 1, 0],
    ],
    "dancehall": [
        [1, 0, 0, 0,  0, 1, 0, 0,  1, 0, 0, 0,  0, 0, 1, 0],
        [1, 0, 0, 1,  0, 0, 0, 1,  1, 0, 0, 0,  1, 0, 0, 0],
    ],
    "r&b": [
        [1, 0, 0, 0,  0, 1, 0, 0,  0, 1, 0, 0,  0, 0, 1, 0],
        [1, 0, 0, 1,  0, 0, 0, 0,  1, 0, 0, 0,  0, 1, 0, 1],
    ],
    "rnb": [
        [1, 0, 0, 0,  0, 1, 0, 0,  0, 1, 0, 0,  0, 0, 1, 0],
        [1, 0, 0, 1,  0, 0, 0, 0,  1, 0, 0, 0,  0, 1, 0, 1],
    ],
    "bachata": [
        [1, 0, 0, 0,  1, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0],
        [1, 0, 1, 0,  0, 0, 1, 0,  0, 1, 0, 0,  0, 0, 0, 0],
    ],
    "amapiano": [
        [1, 0, 0, 1,  0, 0, 1, 0,  0, 0, 1, 0,  1, 0, 0, 0],
        [1, 0, 1, 0,  1, 0, 0, 1,  0, 1, 0, 0,  1, 0, 1, 0],
    ],
    "jersey club": [
        [1, 0, 1, 0,  1, 0, 0, 1,  1, 0, 1, 0,  0, 1, 0, 0],
        [1, 1, 0, 0,  1, 0, 1, 0,  0, 0, 1, 1,  1, 0, 0, 1],
    ],
}

# ── BPM ranges per genre ─────────────────────────────────────────────────────

GENRE_BPM: dict[str, tuple[int, int]] = {
    "trap":         (130, 160),
    "uk drill":     (140, 145),
    "drill":        (140, 145),
    "house":        (120, 130),
    "lo-fi":        (70,  90),
    "lofi":         (70,  90),
    "hip hop":      (85,  100),
    "boom bap":     (85,  100),
    "edm":          (128, 135),
    "reggaeton":    (92,  98),
    "dembow":       (92,  98),
    "afrobeat":     (100, 115),
    "dancehall":    (100, 110),
    "r&b":          (70,  95),
    "rnb":          (70,  95),
    "bachata":      (120, 135),
    "cumbia":       (100, 120),
    "jersey club":  (140, 150),
    "amapiano":     (108, 116),
}

# Bass style per genre: how to generate the bass line
_GENRE_BASS_STYLE: dict[str, str] = {
    "trap":       "808_long",
    "uk drill":   "808_slide",
    "drill":      "808_slide",
    "house":      "walking",
    "lo-fi":      "walking",
    "hip hop":    "root",
    "boom bap":   "root",
    "edm":        "root",
    "reggaeton":  "punchy",
    "dembow":     "punchy",
    "afrobeat":   "walking",
    "dancehall":  "root",
    "r&b":        "melodic",
    "rnb":        "melodic",
    "bachata":    "root",
    "cumbia":     "root",
    "jersey club":"root",
    "amapiano":   "walking",
}

# ── Core functions ────────────────────────────────────────────────────────────

def parse_root(root: str) -> int:
    key = root.upper().strip()
    if len(key) == 2 and key[1] == "B" and key[0] != "B":
        flat_map = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}
        key = flat_map.get(key, key)
    result = _NOTE_TO_SEMI.get(key)
    if result is None:
        raise ValueError(f"Unknown root note: {root!r}")
    return result


def scale_midi_notes(root: str, scale_name: str, octave: int = 4, num_octaves: int = 2) -> list[int]:
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
    root_semi = parse_root(root)
    intervals = SCALES.get(scale_name, SCALES["minor"])
    degree_idx = degree % len(intervals)
    chord_root_offset = intervals[degree_idx]
    chord_root_midi = (octave + 1) * 12 + root_semi + chord_root_offset

    if voicing == "power":
        return [chord_root_midi, chord_root_midi + 7]

    chord_intervals = []
    for step in [0, 2, 4]:
        idx = (degree_idx + step) % len(intervals)
        offset = intervals[idx]
        if idx < degree_idx + step:
            offset += 12
        chord_intervals.append(offset - intervals[degree_idx])

    if voicing == "seventh":
        idx = (degree_idx + 6) % len(intervals)
        offset = intervals[idx]
        if idx < degree_idx + 6:
            offset += 12
        chord_intervals.append(offset - intervals[degree_idx])

    return [chord_root_midi + i for i in chord_intervals if 0 <= chord_root_midi + i <= 127]


def chord_name(root: str, scale_name: str, degree: int) -> str:
    root_semi = parse_root(root)
    intervals = SCALES.get(scale_name, SCALES["minor"])
    degree_idx = degree % len(intervals)
    chord_root_semi = (root_semi + intervals[degree_idx]) % 12
    note = _SEMI_TO_NOTE[chord_root_semi]
    third_step = intervals[(degree_idx + 2) % len(intervals)] - intervals[degree_idx]
    if third_step < 0:
        third_step += 12
    quality = "m" if third_step == 3 else ""
    return f"{note}{quality}"


def get_genre_defaults(genre: str) -> dict:
    genre_lower = genre.lower()
    prog_data = CHORD_PROGRESSIONS.get(genre_lower, CHORD_PROGRESSIONS["hip hop"])
    bpm_range = GENRE_BPM.get(genre_lower, (120, 140))
    return {
        "scale": prog_data["scale"],
        "progression": prog_data["progression"],
        "chord_voicing": prog_data["chord_voicing"],
        "bpm_default": (bpm_range[0] + bpm_range[1]) // 2,
    }


def get_genre_instruments(genre: str) -> dict:
    """Return instrument knowledge for a genre."""
    genre_lower = genre.lower()
    # Try exact match, then aliases
    aliases = {"lofi": "lo-fi", "rnb": "r&b", "dembow": "reggaeton"}
    key = aliases.get(genre_lower, genre_lower)
    return GENRE_INSTRUMENTS.get(key, {})


def generate_drum_notes(genre: str, bars: int, humanize: bool = True) -> list[dict]:
    genre_lower = genre.lower()
    # Alias handling
    aliases = {"lofi": "lo-fi", "rnb": "r&b"}
    genre_lower = aliases.get(genre_lower, genre_lower)

    pattern = DRUM_PATTERNS.get(genre_lower, DRUM_PATTERNS["hip hop"])
    notes = []
    steps_per_bar = 16
    step_duration = 0.25

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
                    "channel": 9,
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
    genre: Optional[str] = None,
) -> list[dict]:
    """Generate bass notes. If genre is given, picks the appropriate style automatically."""
    if genre:
        genre_lower = genre.lower()
        aliases = {"lofi": "lo-fi", "rnb": "r&b"}
        genre_lower = aliases.get(genre_lower, genre_lower)
        style = _GENRE_BASS_STYLE.get(genre_lower, style)

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
        fifth_idx = (degree_idx + 4) % len(intervals)
        bass_fifth = (octave + 1) * 12 + root_semi + intervals[fifth_idx]

        if style == "808_long":
            # Trap: long sustained 808, hits on beat 1 with full bar sustain
            notes.append({
                "note": bass_root,
                "velocity": 100,
                "duration": 3.8,
                "time": beat,
                "channel": 1,
                "track": "bass",
            })

        elif style == "808_slide":
            # UK Drill: two hits per bar to create the slide feel
            notes.append({
                "note": bass_root,
                "velocity": 100,
                "duration": 2.0,
                "time": beat,
                "channel": 1,
                "track": "bass",
            })
            notes.append({
                "note": bass_fifth,
                "velocity": 90,
                "duration": 1.8,
                "time": beat + 2.0,
                "channel": 1,
                "track": "bass",
            })

        elif style == "punchy":
            # Reggaeton/dembow: short punchy bass hits on beats 1 and 3
            for hit_beat in [0.0, 2.0]:
                notes.append({
                    "note": bass_root,
                    "velocity": 95,
                    "duration": 0.4,
                    "time": beat + hit_beat,
                    "channel": 1,
                    "track": "bass",
                })

        elif style == "walking":
            # House/lo-fi: root on beat 1, fifth on beat 3
            notes.append({
                "note": bass_root,
                "velocity": 95,
                "duration": 1.8,
                "time": beat,
                "channel": 1,
                "track": "bass",
            })
            notes.append({
                "note": bass_fifth,
                "velocity": 85,
                "duration": 1.8,
                "time": beat + 2.0,
                "channel": 1,
                "track": "bass",
            })

        elif style == "melodic":
            # R&B: four hits per bar following chord tones
            chord_tones = [bass_root, bass_fifth, bass_root + 4, bass_fifth - 5]
            hit_times = [0.0, 1.0, 2.0, 3.0]
            for i, t in enumerate(hit_times):
                notes.append({
                    "note": chord_tones[i % len(chord_tones)],
                    "velocity": max(70, 95 - i * 5),
                    "duration": 0.8,
                    "time": beat + t,
                    "channel": 1,
                    "track": "bass",
                })

        else:
            # Default: root whole note
            notes.append({
                "note": bass_root,
                "velocity": 100,
                "duration": 3.5,
                "time": beat,
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
    genre: Optional[str] = None,
) -> list[dict]:
    """Generate melody. If genre is given, uses genre-specific rhythm template."""
    scale_notes_list = scale_midi_notes(root, scale_name, octave=octave, num_octaves=2)
    intervals = SCALES.get(scale_name, SCALES["minor"])
    notes = []
    step_dur = 0.25
    bars_per_chord = max(1, bars // len(progression))
    current_note_idx = len(scale_notes_list) // 4

    # Pick rhythm template: genre-specific first, then fallback
    genre_lower = (genre or "hip hop").lower()
    aliases = {"lofi": "lo-fi", "rnb": "r&b"}
    genre_lower = aliases.get(genre_lower, genre_lower)
    rhythms = MELODY_RHYTHMS.get(genre_lower, MELODY_RHYTHMS["hip hop"])

    for bar_idx in range(bars):
        chord_idx = (bar_idx // bars_per_chord) % len(progression)
        degree = progression[chord_idx]
        degree_idx = degree % len(intervals)
        root_semi = parse_root(root)
        chord_root_midi = (octave + 1) * 12 + root_semi + intervals[degree_idx]

        chord_tones = [n for n in scale_notes_list if (n - chord_root_midi) % 12 in [0, 3, 4, 7]]
        if not chord_tones:
            chord_tones = scale_notes_list

        rhythm = rhythms[bar_idx % len(rhythms)]

        for step, hit in enumerate(rhythm):
            if hit == 0:
                continue
            beat_time = bar_idx * 4.0 + step * step_dur

            if random.random() < 0.7 and chord_tones:
                target = min(chord_tones, key=lambda n: abs(n - scale_notes_list[current_note_idx]))
                if target in scale_notes_list:
                    current_note_idx = scale_notes_list.index(target)
            else:
                direction = random.choice([-1, 0, 0, 1])
                current_note_idx = max(0, min(len(scale_notes_list) - 1, current_note_idx + direction))

            midi_note = scale_notes_list[current_note_idx]
            vel = 85 if random.random() > 0.3 else 70
            if humanize:
                vel = max(1, min(127, vel + random.randint(-10, 10)))

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
