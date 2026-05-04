"""
flp_writer.py — Pure Python FL Studio .flp file writer.

No pyflp dependency. Generates a binary .flp compatible with FL Studio 20/21
by writing the event format directly.

FL Studio .flp format:
  "FLhd" + header_len(4) + format(2) + channels(2) + ppq(2)
  "FLdt" + data_len(4) + events...

Event encoding:
  ID 0x00-0x3F → BYTE event:   [id][value_1byte]
  ID 0x40-0x7F → WORD event:   [id][value_2bytes_LE]
  ID 0x80-0xBF → DWORD event:  [id][value_4bytes_LE]
  ID 0xC0-0xFF → VAR event:    [id][varint_length][bytes]
"""

from __future__ import annotations

import struct
from pathlib import Path


FL_PPQ = 96  # ticks per beat (FL Studio default)

# ── Event ID constants ────────────────────────────────────────────────────────
# Source: pyflp source + FL Studio file format community docs

# Project-level (DWORD 0x80-0xBF)
_EV_VERSION   = 0xC7  # VAR  — project version string
_EV_TEMPO     = 0x9C  # DWORD — BPM * 1000
_EV_PPQN      = 0xA4  # WORD  — PPQ (sometimes redundant with header)

# Channel-level (one block per channel)
_EV_CH_NEW    = 0x40  # WORD  — signals a new channel; value = channel index
_EV_CH_TYPE   = 0x15  # BYTE  — 0=sampler, 1=unknown, 2=native FL instrument
_EV_CH_ENABLED= 0x00  # BYTE  — 1=enabled
_EV_CH_VOL    = 0x02  # BYTE  — volume 0-128 (default 100)
_EV_CH_PAN    = 0x03  # BYTE  — pan 0-128 (default 64=center)
_EV_CH_NAME   = 0xC4  # VAR   — channel name, UTF-16-LE null-terminated
_EV_CH_SAMPLE = 0xC5  # VAR   — sample path, UTF-16-LE null-terminated
_EV_CH_COLOR  = 0x83  # DWORD — channel color (RGBA)

# Pattern-level
_EV_PAT_NEW   = 0xE1  # VAR   — new pattern marker
_EV_PAT_NAME  = 0xC1  # VAR   — pattern name, UTF-16-LE null-terminated
_EV_PAT_NOTES = 0xE8  # VAR   — note data, 12 bytes per note
_EV_PAT_COLOR = 0x96  # DWORD — pattern color


def _varint(n: int) -> bytes:
    """Encode n as a variable-length integer (FL Studio format)."""
    result = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            result.append(b | 0x80)
        else:
            result.append(b)
            break
    return bytes(result)


def _byte_ev(eid: int, value: int) -> bytes:
    return bytes([eid & 0xFF, value & 0xFF])


def _word_ev(eid: int, value: int) -> bytes:
    return bytes([eid & 0xFF]) + struct.pack("<H", value & 0xFFFF)


def _dword_ev(eid: int, value: int) -> bytes:
    return bytes([eid & 0xFF]) + struct.pack("<I", value & 0xFFFFFFFF)


def _var_ev(eid: int, data: bytes) -> bytes:
    return bytes([eid & 0xFF]) + _varint(len(data)) + data


def _text_ev(eid: int, text: str) -> bytes:
    """UTF-16-LE null-terminated string event (channel names, pattern names)."""
    encoded = (text + "\x00").encode("utf-16-le")
    return _var_ev(eid, encoded)


def _path_ev(eid: int, path: str) -> bytes:
    """ASCII null-terminated string event (sample file paths)."""
    encoded = path.encode("ascii", errors="replace") + b"\x00"
    return _var_ev(eid, encoded)


# ── Channel builder ───────────────────────────────────────────────────────────

def _channel_events(index: int, name: str, sample_path: str | None, color: int = 0x5A7BBF) -> bytes:
    ev = bytearray()
    ev += _word_ev(_EV_CH_NEW, index)
    ev += _byte_ev(_EV_CH_ENABLED, 1)
    ev += _byte_ev(_EV_CH_TYPE, 0 if sample_path else 2)
    ev += _byte_ev(_EV_CH_VOL, 100)
    ev += _byte_ev(_EV_CH_PAN, 64)
    ev += _dword_ev(_EV_CH_COLOR, color)
    ev += _text_ev(_EV_CH_NAME, name)
    if sample_path:
        ev += _path_ev(_EV_CH_SAMPLE, sample_path)
    return bytes(ev)


# ── Pattern builder ───────────────────────────────────────────────────────────

def _note_bytes(
    pos_ticks: int,
    len_ticks: int,
    key: int,
    channel: int,
    velocity: int,
    pan: int = 64,
) -> bytes:
    """
    12 bytes per note (FL Studio note struct):
      pos(4) + length(4) + key(1) + fine_pitch(1) + channel(1) + pan(1) +
      velocity(1) + mod_x(1) + mod_y(1) + flags(1)
    """
    return struct.pack(
        "<IIBBBBBBBb",
        pos_ticks & 0xFFFFFFFF,
        len_ticks & 0xFFFFFFFF,
        key & 0x7F,
        0,           # fine pitch
        channel & 0xFF,
        pan & 0xFF,
        velocity & 0x7F,
        128,         # mod_x default
        128,         # mod_y default
        0,           # flags
    )


def _pattern_events(index: int, name: str, notes: list[dict]) -> bytes:
    ev = bytearray()
    ev += _var_ev(_EV_PAT_NEW, struct.pack("<H", index))
    ev += _text_ev(_EV_PAT_NAME, name)

    if notes:
        note_data = bytearray()
        for nd in notes:
            note_data += _note_bytes(
                pos_ticks=int(nd["pos"]),
                len_ticks=max(1, int(nd["len"])),
                key=int(nd["key"]),
                channel=int(nd["ch"]),
                velocity=max(1, min(127, int(nd["vel"]))),
            )
        ev += _var_ev(_EV_PAT_NOTES, bytes(note_data))

    return bytes(ev)


# ── Public API ────────────────────────────────────────────────────────────────

def write_flp(
    output_path: str,
    bpm: float,
    channels: list[dict],
    notes: list[dict],
    ppq: int = FL_PPQ,
    pattern_name: str = "Pattern 1",
) -> None:
    """
    Write a minimal FL Studio .flp file.

    channels: list of {"name": str, "sample_path": str|None, "color": int}
    notes:    list of {"pos": ticks, "len": ticks, "key": midi, "ch": rack_idx, "vel": 0-127}
    """
    events = bytearray()

    # Project version (helps FL Studio identify the format)
    events += _text_ev(_EV_VERSION, "20.9.2")

    # BPM
    events += _dword_ev(_EV_TEMPO, int(bpm * 1000))

    # Channels
    colors = [
        0xFF4040, 0xFF8040, 0xFFB040,  # kick, snare, clap
        0x40C040, 0x40C0A0, 0x4060FF,  # hihat, open hh, crash
        0xFF4080, 0xA040FF, 0x40A0FF,  # 808, melody, chords
    ]
    for i, ch in enumerate(channels):
        color = ch.get("color", colors[i % len(colors)])
        events += _channel_events(i, ch["name"], ch.get("sample_path"), color)

    # Pattern 1
    events += _pattern_events(1, pattern_name, notes)

    events_bytes = bytes(events)

    header = (
        b"FLhd"
        + struct.pack("<I", 6)
        + struct.pack("<H", 0)
        + struct.pack("<H", len(channels))
        + struct.pack("<H", ppq)
    )

    data_section = (
        b"FLdt"
        + struct.pack("<I", len(events_bytes))
        + events_bytes
    )

    Path(output_path).write_bytes(header + data_section)
