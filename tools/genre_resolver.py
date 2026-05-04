"""
genre_resolver.py — resolve unknown genres via Claude API.

When a genre isn't in DRUM_PATTERNS or CHORD_PROGRESSIONS, this module calls
the Anthropic API to get structured musical data (drum pattern, scale, chords,
instruments) and caches the result so the API is only called once per genre.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import config as cfg

# ── Cache ────────────────────────────────────────────────────────────────────

def _cache_path() -> Path:
    return cfg.cache_folder() / "genre_cache.json"


def _load_cache() -> dict:
    p = _cache_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(data: dict) -> None:
    try:
        _cache_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── Anthropic API key ─────────────────────────────────────────────────────────

def _api_key() -> str | None:
    cfg_data = cfg.get_config()
    key = cfg_data.get("anthropic_api_key", "")
    if key:
        return key
    import os
    return os.environ.get("ANTHROPIC_API_KEY") or None


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a music production expert with deep knowledge of every music genre worldwide. "
    "When given a genre name, you return a JSON object with its musical characteristics "
    "formatted for a drum machine and MIDI sequencer. "
    "Be precise and authentic to the real genre — not generic."
)

_USER_TEMPLATE = """
Describe the genre "{genre}" for a MIDI beat generator. Return ONLY valid JSON, no explanation.

The JSON must have exactly these fields:

{{
  "bpm_range": [min_bpm, max_bpm],
  "scale": "<one of: minor, major, pentatonic_minor, pentatonic_major, dorian, phrygian, blues, harmonic_minor>",
  "progression": [d0, d1, d2, d3],
  "chord_voicing": "<one of: minor_triad, power, seventh>",
  "bass_style": "<one of: root, walking, punchy, 808_long, 808_slide, melodic>",
  "drum_pattern": {{
    "kick":         [16 values, each 0-127, velocity or 0 for rest],
    "snare":        [16 values],
    "hihat_closed": [16 values],
    "hihat_open":   [16 values],
    "clap":         [16 values]
  }},
  "melody_rhythms": [
    [16 values, each 0 or 1],
    [16 values, each 0 or 1]
  ],
  "instruments": {{
    "drums":     ["list of drum sounds/instruments typical for this genre"],
    "bass":      ["list of bass sounds/instruments"],
    "melody":    ["list of melodic instruments"],
    "chords":    ["list of harmonic instruments"],
    "signature": "one sentence describing the defining sonic element of this genre",
    "key_plugins": ["VST plugins commonly used"],
    "avoid":     ["what NOT to use in this genre"]
  }}
}}

Rules for drum_pattern:
- 16 steps = 1 bar of 16th notes. Steps 0,4,8,12 = beats 1,2,3,4.
- Velocity 100 = strong hit, 70 = medium, 40 = ghost note, 0 = rest.
- Be accurate to how this genre actually sounds.

Rules for progression:
- Each value is a scale degree index (0-based). 0=root, 1=2nd degree, 2=3rd, 3=4th, 4=5th, 5=6th, 6=7th.
- Example minor i-VI-III-VII = [0, 5, 2, 6]
"""


def _call_claude(genre: str, api_key: str) -> dict | None:
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _USER_TEMPLATE.format(genre=genre)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()

        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return json.loads(text)
    except Exception:
        return None


# ── Validation and normalization ──────────────────────────────────────────────

_VALID_SCALES = {"minor", "major", "pentatonic_minor", "pentatonic_major", "dorian", "phrygian", "blues", "harmonic_minor"}
_VALID_VOICINGS = {"minor_triad", "power", "seventh"}
_VALID_BASS_STYLES = {"root", "walking", "punchy", "808_long", "808_slide", "melodic"}


def _validate(data: dict) -> bool:
    """Basic structural check before trusting Claude's output."""
    try:
        assert isinstance(data.get("bpm_range"), list) and len(data["bpm_range"]) == 2
        assert data.get("scale") in _VALID_SCALES
        assert isinstance(data.get("progression"), list) and len(data["progression"]) == 4
        assert data.get("chord_voicing") in _VALID_VOICINGS
        assert data.get("bass_style") in _VALID_BASS_STYLES
        dp = data.get("drum_pattern", {})
        for key in ("kick", "snare", "hihat_closed", "hihat_open", "clap"):
            assert isinstance(dp.get(key), list) and len(dp[key]) == 16
        rhythms = data.get("melody_rhythms", [])
        assert isinstance(rhythms, list) and len(rhythms) == 2
        assert all(isinstance(r, list) and len(r) == 16 for r in rhythms)
        return True
    except AssertionError:
        return False


def _normalize(data: dict, genre: str) -> dict:
    """Clamp velocities, ensure all values are ints, fill missing fields."""
    dp = data["drum_pattern"]
    for key in dp:
        dp[key] = [max(0, min(127, int(v))) for v in dp[key]]

    rhythms = data["melody_rhythms"]
    data["melody_rhythms"] = [[1 if v else 0 for v in r] for r in rhythms]

    data["progression"] = [max(0, min(6, int(d))) for d in data["progression"]]
    data["bpm_range"] = [int(data["bpm_range"][0]), int(data["bpm_range"][1])]

    if "instruments" not in data:
        data["instruments"] = {
            "drums": [], "bass": [], "melody": [], "chords": [],
            "signature": f"AI-resolved genre: {genre}",
            "key_plugins": [], "avoid": [],
        }

    data["_source"] = "claude_api"
    data["_genre"] = genre
    return data


# ── Public API ────────────────────────────────────────────────────────────────

def resolve_genre(genre: str) -> dict | None:
    """
    Return genre data for use in beat generation.

    Checks cache first. If not cached, calls Claude API and caches the result.
    Returns None if resolution fails (no API key, network error, bad response).
    """
    genre_lower = genre.lower().strip()

    # Check cache
    cache = _load_cache()
    if genre_lower in cache:
        return cache[genre_lower]

    # Need API key to proceed
    api_key = _api_key()
    if not api_key:
        return None

    data = _call_claude(genre_lower, api_key)
    if data is None:
        return None

    if not _validate(data):
        return None

    data = _normalize(data, genre_lower)

    # Cache it
    cache[genre_lower] = data
    _save_cache(cache)

    return data


def genre_to_music_theory(resolved: dict) -> dict:
    """
    Convert a resolved genre dict into the format music_theory.py functions expect.
    Returns a dict with keys: drum_pattern, chord_progression, bpm_range,
    melody_rhythms, bass_style, instruments.
    """
    return {
        "drum_pattern": resolved["drum_pattern"],
        "chord_progression": {
            "scale": resolved["scale"],
            "progression": resolved["progression"],
            "chord_voicing": resolved["chord_voicing"],
        },
        "bpm_range": tuple(resolved["bpm_range"]),
        "melody_rhythms": resolved["melody_rhythms"],
        "bass_style": resolved["bass_style"],
        "instruments": resolved.get("instruments", {}),
    }
