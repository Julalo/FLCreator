"""
flp_diagnose.py — read a .flp file and dump its raw event structure.

Used to reverse-engineer the exact event IDs and encodings that a specific
FL Studio version uses, so flp_writer.py can match them exactly.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Optional

from fastmcp import Context

import config as cfg


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Read a variable-length integer. Returns (value, new_offset)."""
    result = 0
    shift = 0
    while offset < len(data):
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    return result, offset


def _try_decode(raw: bytes) -> str:
    """Try to decode bytes as UTF-16-LE, UTF-8, or ASCII."""
    # Try UTF-16-LE (null-terminated)
    if len(raw) >= 2 and len(raw) % 2 == 0:
        try:
            text = raw.decode("utf-16-le")
            text = text.rstrip("\x00")
            if text and all(32 <= ord(c) < 127 or c in "\n\r\t" for c in text):
                return f'utf16: "{text}"'
            elif text:
                return f'utf16: "{text[:60]}..."' if len(text) > 60 else f'utf16: "{text}"'
        except Exception:
            pass

    # Try ASCII / UTF-8
    try:
        text = raw.decode("ascii").rstrip("\x00")
        if text:
            return f'ascii: "{text[:80]}"'
    except Exception:
        pass

    try:
        text = raw.decode("utf-8").rstrip("\x00")
        if text:
            return f'utf8: "{text[:80]}"'
    except Exception:
        pass

    return f"raw({len(raw)}b): {raw[:24].hex()}"


def parse_flp_events(flp_path: str) -> list[dict]:
    """Parse a .flp file and return a list of events with their IDs and values."""
    data = Path(flp_path).read_bytes()

    # Validate header
    if data[:4] != b"FLhd":
        return [{"error": "Not a valid .flp file (missing FLhd)"}]

    hdr_len = struct.unpack_from("<I", data, 4)[0]
    fmt     = struct.unpack_from("<H", data, 8)[0]
    channels= struct.unpack_from("<H", data, 10)[0]
    ppq     = struct.unpack_from("<H", data, 12)[0]

    events = [{
        "type": "HEADER",
        "format": fmt,
        "channels": channels,
        "ppq": ppq,
    }]

    # Find FLdt
    offset = 8 + hdr_len  # skip past header data
    if data[offset:offset+4] != b"FLdt":
        return events + [{"error": "Missing FLdt section"}]

    data_len = struct.unpack_from("<I", data, offset + 4)[0]
    offset += 8
    end = offset + data_len

    while offset < end:
        eid = data[offset]
        offset += 1

        if eid < 0x40:
            # BYTE event
            val = data[offset]
            offset += 1
            events.append({"eid": eid, "eid_hex": hex(eid), "type": "BYTE", "value": val})

        elif eid < 0x80:
            # WORD event
            val = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            events.append({"eid": eid, "eid_hex": hex(eid), "type": "WORD", "value": val})

        elif eid < 0xC0:
            # DWORD event
            val = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            events.append({"eid": eid, "eid_hex": hex(eid), "type": "DWORD", "value": val})

        else:
            # VAR event
            length, offset = _read_varint(data, offset)
            raw = data[offset:offset + length]
            offset += length
            decoded = _try_decode(raw)
            events.append({
                "eid": eid,
                "eid_hex": hex(eid),
                "type": "VAR",
                "length": length,
                "decoded": decoded,
            })

    return events


async def diagnose_flp(flp_path: str, ctx: Optional[Context] = None) -> dict:
    """
    Read a .flp file and dump its event structure.
    Used to find correct event IDs for flp_writer.py.
    """
    p = Path(flp_path)
    if not p.exists():
        return {"error": f"File not found: {flp_path}"}
    if p.suffix.lower() != ".flp":
        return {"error": "Not a .flp file"}

    try:
        events = parse_flp_events(flp_path)
    except Exception as exc:
        return {"error": f"Failed to parse: {exc}"}

    # Summarize: show first 80 events to avoid overwhelming output
    total = len(events)
    preview = events[:80]

    # Group VAR events that look like paths or names
    strings = [
        e for e in events
        if e.get("type") == "VAR" and e.get("decoded", "").startswith(("ascii:", "utf16:"))
    ]

    return {
        "file": flp_path,
        "total_events": total,
        "events": preview,
        "string_events": strings[:20],
        "note": f"Showing first 80 of {total} events. String events show channel names, sample paths, etc.",
    }
