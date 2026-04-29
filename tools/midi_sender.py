"""
midi_sender.py — send_notes MCP tool.
Sends MIDI notes to FL Studio via a LoopMIDI virtual port.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from fastmcp import Context

import config as cfg


def _find_loopback_port(port_name: Optional[str] = None) -> str | None:
    """Return the name of a suitable MIDI output port."""
    try:
        import mido  # type: ignore
        ports = mido.get_output_names()
    except Exception:
        return None

    if port_name:
        for p in ports:
            if port_name.lower() in p.lower():
                return p
        return None

    # Auto-detect LoopMIDI port
    preferred = [cfg.midi_port_name().lower(), "loopmidi", "loopbe", "midi yoke"]
    for pref in preferred:
        for p in ports:
            if pref in p.lower():
                return p

    # Fallback to first available port
    return ports[0] if ports else None


def _note_to_midi(note_input) -> int:
    """Accept int (0-127) or note name string like 'C4', 'F#3'."""
    if isinstance(note_input, int):
        return max(0, min(127, note_input))
    if isinstance(note_input, str):
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        note_input = note_input.strip().upper()
        import re
        m = re.match(r"([A-G]#?)(-?\d+)", note_input)
        if m:
            name, octave = m.group(1), int(m.group(2))
            if name in note_names:
                return (octave + 1) * 12 + note_names.index(name)
    return 60  # Middle C as safe default


async def send_notes(
    notes: list[dict],
    port_name: Optional[str] = None,
    bpm: Optional[float] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Send MIDI notes to FL Studio via a LoopMIDI virtual port.

    Each note dict: {note, velocity, duration (beats), time (beats)}
    """
    if not notes:
        return {"error": "No notes provided.", "sent": 0}

    try:
        import mido  # type: ignore
    except ImportError:
        return {
            "error": "mido is not installed. Run: pip install mido python-rtmidi",
            "sent": 0,
        }

    actual_port = _find_loopback_port(port_name)
    if actual_port is None:
        available: list[str] = []
        try:
            available = mido.get_output_names()
        except Exception:
            pass
        return {
            "error": (
                "No LoopMIDI port found. "
                "Install LoopMIDI (Windows) and create a virtual port. "
                f"Available ports: {available}"
            ),
            "sent": 0,
        }

    if ctx:
        await ctx.log_info(f"Sending {len(notes)} notes via MIDI port '{actual_port}'")

    actual_bpm = bpm or cfg.default_bpm()
    seconds_per_beat = 60.0 / actual_bpm

    # Sort notes by start time
    sorted_notes = sorted(notes, key=lambda n: n.get("time", 0))

    sent = 0
    errors: list[str] = []

    def _send_blocking():
        nonlocal sent
        try:
            with mido.open_output(actual_port) as port:
                # Use absolute time scheduling relative to start
                wall_start = time.time()

                for note_data in sorted_notes:
                    try:
                        note_num = _note_to_midi(note_data.get("note", 60))
                        velocity = max(0, min(127, int(note_data.get("velocity", cfg.default_velocity()))))
                        duration_beats = float(note_data.get("duration", 0.25))
                        start_beats = float(note_data.get("time", 0))

                        start_sec = start_beats * seconds_per_beat
                        duration_sec = duration_beats * seconds_per_beat

                        # Wait until note start time
                        now = time.time() - wall_start
                        if start_sec > now:
                            time.sleep(start_sec - now)

                        port.send(mido.Message("note_on", note=note_num, velocity=velocity))
                        time.sleep(duration_sec)
                        port.send(mido.Message("note_off", note=note_num, velocity=0))
                        sent += 1

                    except Exception as exc:
                        errors.append(str(exc))

        except Exception as exc:
            errors.append(f"Port error: {exc}")

    await asyncio.to_thread(_send_blocking)

    if ctx:
        await ctx.log_info(f"Sent {sent}/{len(notes)} notes. Errors: {len(errors)}")

    result = {
        "success": sent == len(notes),
        "sent": sent,
        "total": len(notes),
        "port": actual_port,
        "bpm": actual_bpm,
    }
    if errors:
        result["errors"] = errors
    return result
