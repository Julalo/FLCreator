"""
project_reader.py — read_project MCP tool.
Parses FL Studio .flp project files using pyflp.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastmcp import Context


def _safe_str(val) -> str | None:
    try:
        return str(val) if val is not None else None
    except Exception:
        return None


async def read_project(
    project_path: str,
    ctx: Optional[Context] = None,
) -> dict:
    flp = Path(project_path)
    if not flp.exists():
        return {"error": f"File not found: {project_path}"}
    if flp.suffix.lower() != ".flp":
        return {"error": f"Not a .flp file: {project_path}"}

    try:
        import pyflp  # type: ignore
    except ImportError:
        return {
            "error": (
                "pyflp is not installed. Run: pip install pyflp\n"
                "Note: pyflp may not support all FL Studio versions."
            )
        }

    if ctx:
        await ctx.log_info(f"Parsing project: {flp.name}")

    try:
        project = pyflp.parse(str(flp))
    except Exception as exc:
        return {"error": f"Failed to parse .flp: {exc}", "path": project_path}

    result: dict = {
        "path": project_path,
        "filename": flp.name,
    }

    # BPM
    try:
        result["bpm"] = float(project.tempo)
    except Exception:
        result["bpm"] = None

    # Title / metadata
    try:
        result["title"] = _safe_str(getattr(project, "title", None))
    except Exception:
        result["title"] = None

    try:
        result["author"] = _safe_str(getattr(project, "artist", None))
    except Exception:
        result["author"] = None

    try:
        result["genre"] = _safe_str(getattr(project, "genre", None))
    except Exception:
        result["genre"] = None

    try:
        result["comments"] = _safe_str(getattr(project, "comment", None))
    except Exception:
        result["comments"] = None

    # Channels
    channels: list[dict] = []
    try:
        for ch in project.channels:
            ch_data: dict = {
                "name": _safe_str(getattr(ch, "name", None)),
                "color": _safe_str(getattr(ch, "color", None)),
                "type": _safe_str(type(ch).__name__),
            }
            # Try to get plugin/sample info
            try:
                ch_data["plugin"] = _safe_str(getattr(ch, "plugin", None))
            except Exception:
                pass
            try:
                sample_path = getattr(ch, "sample_path", None)
                ch_data["sample_path"] = _safe_str(sample_path)
            except Exception:
                pass
            channels.append(ch_data)
    except Exception as exc:
        if ctx:
            await ctx.log_error(f"Error reading channels: {exc}")

    result["channels"] = channels
    result["channel_count"] = len(channels)

    # Patterns
    patterns: list[dict] = []
    try:
        for pat in project.patterns:
            pat_data: dict = {
                "name": _safe_str(getattr(pat, "name", None)),
                "color": _safe_str(getattr(pat, "color", None)),
            }
            try:
                notes = getattr(pat, "notes", [])
                pat_data["note_count"] = len(list(notes))
            except Exception:
                pat_data["note_count"] = None
            patterns.append(pat_data)
    except Exception as exc:
        if ctx:
            await ctx.log_error(f"Error reading patterns: {exc}")

    result["patterns"] = patterns
    result["pattern_count"] = len(patterns)

    # Mixer
    mixer_tracks: list[dict] = []
    try:
        for track in project.mixer.tracks:
            mixer_tracks.append({
                "name": _safe_str(getattr(track, "name", None)),
                "volume": _safe_str(getattr(track, "volume", None)),
                "pan": _safe_str(getattr(track, "pan", None)),
            })
    except Exception:
        pass

    result["mixer_tracks"] = mixer_tracks
    result["mixer_track_count"] = len(mixer_tracks)

    if ctx:
        await ctx.log_info(
            f"Parsed: {result.get('channel_count', 0)} channels, "
            f"{result.get('pattern_count', 0)} patterns, "
            f"BPM={result.get('bpm')}"
        )

    return result
