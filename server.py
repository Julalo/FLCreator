"""
server.py — FL Studio Producer Brain MCP Server entry point.

Run with:
    python server.py
or via Claude Desktop / Claude Code after adding it to claude_desktop_config.json.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Any

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

import config as cfg
from classifier.predict import _load_model
from tools.sample_scanner import scan_samples as _scan_samples, get_samples as _get_samples
from tools.plugin_reader import read_plugins as _read_plugins
from tools.plugin_researcher import research_plugin as _research_plugin
from tools.preset_finder import find_presets as _find_presets
from tools.preset_installer import install_preset as _install_preset, load_preset_in_fl as _load_preset_in_fl
from tools.midi_sender import send_notes as _send_notes
from tools.project_reader import read_project as _read_project
from tools.sample_downloader import find_sample_packs as _find_sample_packs, download_sample_pack as _download_sample_pack
from tools.freesound_downloader import search_freesound as _search_freesound, download_freesound_samples as _download_freesound_samples


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialize classifier model and cache dirs at startup."""
    cfg.cache_folder().mkdir(parents=True, exist_ok=True)
    _load_model()  # Pre-load ML model (no-op if not trained yet)
    yield


mcp = FastMCP(
    name="fl-studio-producer-brain",
    lifespan=lifespan,
)


# ── Shared error handler ───────────────────────────────────────────────────────

def _handle_error(exc: Exception, context: str = "") -> dict:
    msg = f"{context}: {exc}" if context else str(exc)
    return {"error": msg, "type": type(exc).__name__}


# ── Input models (Pydantic v2) ─────────────────────────────────────────────────

class ScanSamplesInput(BaseModel):
    folder_path: str = Field(
        ...,
        description="Absolute path to the folder containing audio samples to scan (recursive).",
        min_length=1,
    )
    force_rescan: bool = Field(
        False,
        description="If True, ignore existing cache and re-classify all files.",
    )


class GetSamplesInput(BaseModel):
    type: Optional[str] = Field(
        None,
        description=(
            "Filter by sample type. One of: kick, snare, hihat_closed, hihat_open, "
            "clap, tom, crash, ride, percussion, 808, fx, loop, one_shot, vocal, other."
        ),
    )
    min_confidence: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Minimum classifier confidence (0-1). Default 0.7.",
    )
    sort_by: str = Field(
        "confidence",
        description="Sort field: confidence | brightness | duration | bpm.",
    )


class ReadPluginsInput(BaseModel):
    force_rescan: bool = Field(
        False,
        description="If True, ignore cache and re-scan all plugin folders.",
    )


class ResearchPluginInput(BaseModel):
    plugin_name: str = Field(
        ...,
        description="Name of the plugin to research (e.g. 'Serum', 'Massive', 'Kontakt').",
        min_length=1,
    )


class FindPresetsInput(BaseModel):
    plugin_name: str = Field(
        ...,
        description="Plugin to search presets for (e.g. 'Serum', 'Vital', 'Sylenth1').",
        min_length=1,
    )
    genre: str = Field(
        ...,
        description="Target genre (e.g. 'trap', 'uk drill', 'house', 'lo-fi', 'edm').",
        min_length=1,
    )
    sound_type: Optional[str] = Field(
        None,
        description="Desired sound type: bass, lead, pad, pluck, arp, sfx, etc.",
    )
    free_only: bool = Field(
        True,
        description="If True, only return free presets.",
    )


class InstallPresetInput(BaseModel):
    preset_url: str = Field(
        ...,
        description="Direct download URL for the preset file (.fst, .fxp, .fxb, or .zip).",
        min_length=10,
    )
    plugin_name: str = Field(
        ...,
        description="Plugin name this preset targets (used to find the correct install folder).",
        min_length=1,
    )
    preset_name: str = Field(
        ...,
        description="Human-readable name to identify this preset in the local cache.",
        min_length=1,
    )


class LoadPresetInFLInput(BaseModel):
    preset_path: str = Field(
        ...,
        description="Absolute path to the .fst preset file to load.",
        min_length=1,
    )
    channel_index: Optional[int] = Field(
        None,
        ge=0,
        description="Target channel index in the Channel Rack (0-based). If omitted, uses the current channel.",
    )


class NoteDict(BaseModel):
    note: Any = Field(
        ...,
        description="MIDI note: integer 0-127 or note name string like 'C4', 'F#3'.",
    )
    velocity: int = Field(
        100,
        ge=0,
        le=127,
        description="Note velocity (0-127).",
    )
    duration: float = Field(
        0.25,
        gt=0,
        description="Note duration in beats.",
    )
    time: float = Field(
        0.0,
        ge=0,
        description="Note start position in beats (from sequence start).",
    )


class SendNotesInput(BaseModel):
    notes: List[NoteDict] = Field(
        ...,
        description="List of MIDI notes to send.",
        min_length=1,
    )
    port_name: Optional[str] = Field(
        None,
        description="Name of the LoopMIDI virtual port. Auto-detected if omitted.",
    )
    bpm: Optional[float] = Field(
        None,
        gt=20,
        lt=400,
        description="BPM for timing calculations. Uses config default if omitted.",
    )


class ReadProjectInput(BaseModel):
    project_path: str = Field(
        ...,
        description="Absolute path to the FL Studio .flp project file.",
        min_length=1,
    )


class SuggestForGenreInput(BaseModel):
    genre: str = Field(
        ...,
        description="Target genre (e.g. 'trap', 'uk drill', 'house', 'lo-fi').",
        min_length=1,
    )
    element: str = Field(
        ...,
        description="Musical element needed: drums, bass, melody, pad, lead, all.",
        min_length=1,
    )


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def scan_samples(input: ScanSamplesInput, ctx: Context) -> dict:
    """
    Scan a folder recursively for audio samples and classify each file.

    Uses a three-tier classifier: ML Random Forest → filename heuristics → spectral heuristics.
    Results are cached in cache/samples_library.json for instant future queries.
    Run this once (or with force_rescan=True when you add new samples).
    """
    try:
        return await _scan_samples(
            folder_path=input.folder_path,
            force_rescan=input.force_rescan,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "scan_samples")


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_samples(input: GetSamplesInput, ctx: Context) -> dict:
    """
    Query the local sample library (must run scan_samples first).

    Filter by type, confidence threshold, and sort order.
    Returns matching samples with path, type, BPM, brightness, confidence.
    """
    try:
        return await _get_samples(
            type=input.type,
            min_confidence=input.min_confidence,
            sort_by=input.sort_by,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "get_samples")


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def read_plugins(input: ReadPluginsInput, ctx: Context) -> dict:
    """
    Read all VST plugins installed on this machine and in FL Studio's plugin database.

    Scans FL Studio's plugin database folders and system VST/VST3 directories.
    Results cached in cache/plugins_library.json.
    """
    try:
        return await _read_plugins(force_rescan=input.force_rescan, ctx=ctx)
    except Exception as exc:
        return _handle_error(exc, "read_plugins")


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def research_plugin(input: ResearchPluginInput, ctx: Context) -> dict:
    """
    Fetch and cache information about a specific plugin.

    Returns synthesis type, recommended genres, sound types, and useful links.
    Uses a built-in knowledge base for common plugins (Serum, Massive, Vital, etc.)
    and falls back to web search for lesser-known ones.
    """
    try:
        return await _research_plugin(plugin_name=input.plugin_name, ctx=ctx)
    except Exception as exc:
        return _handle_error(exc, "research_plugin")


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def find_presets(input: FindPresetsInput, ctx: Context) -> dict:
    """
    Search online for presets matching a plugin and genre.

    Queries PresetShare, ADSR Sounds (free tier), Splice free, and official manufacturer pages.
    Returns a list of presets with names, sources, links, and genre tags.
    Use install_preset to download and install any result.
    """
    try:
        return await _find_presets(
            plugin_name=input.plugin_name,
            genre=input.genre,
            sound_type=input.sound_type,
            free_only=input.free_only,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "find_presets")


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def install_preset(input: InstallPresetInput, ctx: Context) -> dict:
    """
    Download a preset file from a URL and install it in the correct FL Studio folder.

    Handles .fst, .fxp, .fxb, and .zip archives (auto-extracts).
    Resolves the install destination based on the plugin name (e.g. Serum → Xfer/Serum Presets/).
    Records the installation in cache/presets_cache.json.
    """
    try:
        return await _install_preset(
            preset_url=input.preset_url,
            plugin_name=input.plugin_name,
            preset_name=input.preset_name,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "install_preset")


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def load_preset_in_fl(input: LoadPresetInFLInput, ctx: Context) -> dict:
    """
    Load a .fst preset into an open FL Studio session using UI automation (pyautogui).

    Requires FL Studio to be running on this machine.
    Opens the FL Studio browser (F8) and positions the cursor for drag-and-drop.
    Note: Full drag automation may require FL Studio in windowed mode.
    If automation fails, the tool returns clear manual fallback instructions.
    """
    try:
        return await _load_preset_in_fl(
            preset_path=input.preset_path,
            channel_index=input.channel_index,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "load_preset_in_fl")


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def send_notes(input: SendNotesInput, ctx: Context) -> dict:
    """
    Send MIDI notes to FL Studio via a LoopMIDI virtual port.

    Requires LoopMIDI (Windows) to be installed and a virtual port created.
    In FL Studio: Options → MIDI → enable the LoopMIDI input port.
    Notes are specified with pitch (0-127 or 'C4'), velocity, duration (beats), and start time (beats).
    """
    try:
        notes_raw = [n.model_dump() for n in input.notes]
        return await _send_notes(
            notes=notes_raw,
            port_name=input.port_name,
            bpm=input.bpm,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "send_notes")


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def read_project(input: ReadProjectInput, ctx: Context) -> dict:
    """
    Parse an FL Studio .flp project file and extract its contents.

    Returns: BPM, title, author, genre, channel list (with plugin/sample names),
    pattern list (with note counts), and mixer track layout.
    Requires pyflp: pip install pyflp
    """
    try:
        return await _read_project(project_path=input.project_path, ctx=ctx)
    except Exception as exc:
        return _handle_error(exc, "read_project")


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def suggest_for_genre(input: SuggestForGenreInput, ctx: Context) -> dict:
    """
    High-level genre advisor that combines your sample library, plugins, and online preset search.

    Given a genre (e.g. 'uk drill') and element (e.g. 'drums'), returns:
    - Recommended samples from your library matching that sound
    - Which of your installed plugins are best suited
    - Preset search results for the best plugins
    - Production tips for the genre
    """
    genre = input.genre.lower()
    element = input.element.lower()

    result: dict = {
        "genre": genre,
        "element": element,
        "samples": [],
        "plugins": [],
        "preset_suggestions": [],
        "tips": [],
    }

    # Genre → sample type mapping
    genre_sample_map: dict[str, list[str]] = {
        "trap": ["kick", "808", "hihat_closed", "hihat_open", "snare", "clap"],
        "uk drill": ["kick", "808", "hihat_closed", "snare"],
        "drill": ["kick", "808", "hihat_closed", "snare"],
        "house": ["kick", "hihat_closed", "snare", "clap", "loop"],
        "lo-fi": ["kick", "snare", "hihat_closed", "loop"],
        "lofi": ["kick", "snare", "hihat_closed", "loop"],
        "edm": ["kick", "snare", "hihat_closed", "clap", "loop"],
        "dnb": ["kick", "snare", "loop"],
        "hip hop": ["kick", "snare", "hihat_closed", "808"],
        "boom bap": ["kick", "snare", "hihat_closed"],
        "ambient": ["loop", "fx", "one_shot"],
        "techno": ["kick", "hihat_closed", "clap", "loop"],
        "trance": ["kick", "snare", "hihat_closed", "loop"],
    }

    # Genre → plugin type suggestions (from built-in knowledge)
    genre_plugin_map: dict[str, list[str]] = {
        "trap": ["serum", "kontakt", "3xosc"],
        "uk drill": ["serum", "kontakt", "vital"],
        "drill": ["serum", "kontakt", "vital"],
        "house": ["sylenth1", "serum", "massive"],
        "lo-fi": ["kontakt", "vital", "harmor"],
        "lofi": ["kontakt", "vital", "harmor"],
        "edm": ["serum", "sylenth1", "nexus"],
        "hip hop": ["kontakt", "3xosc", "serum"],
        "boom bap": ["kontakt", "3xosc"],
        "ambient": ["omnisphere", "vital", "harmor"],
        "techno": ["massive", "serum", "vital"],
        "trance": ["sylenth1", "serum", "nexus"],
    }

    # Genre tips
    genre_tips: dict[str, list[str]] = {
        "trap": [
            "Layer a 808 with a short kick for punch + sustain.",
            "Use triplet hi-hat patterns (1/8T, 1/16T) for that rolling feel.",
            "Side-chain the 808 to the kick for clean low-end.",
            "Pitch the 808 chromatically to match the melody root note.",
        ],
        "uk drill": [
            "Keep the kick on beat 1 and 3, snare on 2 and 4 with rolls.",
            "Offbeat hi-hats with lots of open hi-hats are characteristic.",
            "Dark, minor key melodies (often C minor or F# minor).",
            "Slide the 808 between notes for the glide effect.",
        ],
        "house": [
            "Four-on-the-floor kick pattern is mandatory.",
            "Clap or snare on beats 2 and 4.",
            "Open hi-hats on the off-beats (the 'and' between kicks).",
            "Use chord stabs with a light chop/gate effect.",
        ],
        "lo-fi": [
            "Add vinyl crackle and record noise for texture.",
            "Use a lofi-style drum machine (MPC 60, SP-404 style).",
            "Detune instruments slightly for that imperfect feel.",
            "Chop and rearrange jazz/soul samples for the melody.",
        ],
    }

    # Element → sample types
    element_sample_map: dict[str, list[str]] = {
        "drums": ["kick", "snare", "hihat_closed", "hihat_open", "clap", "tom", "crash", "ride", "percussion"],
        "bass": ["808"],
        "melody": ["one_shot", "loop"],
        "pad": ["loop", "one_shot"],
        "lead": ["one_shot"],
        "fx": ["fx"],
        "all": None,  # None means return all
    }

    target_types = element_sample_map.get(element)
    genre_types = genre_sample_map.get(genre, [])

    if target_types is None:
        filter_types = genre_types or None
    else:
        filter_types = [t for t in target_types if not genre_types or t in genre_types] or target_types

    # Get samples from library
    try:
        for stype in (filter_types or [None]):  # type: ignore
            samples_result = await _get_samples(
                type=stype,
                min_confidence=0.65,
                sort_by="confidence",
                ctx=ctx,
            )
            result["samples"].extend(samples_result.get("samples", [])[:5])
    except Exception as exc:
        result["samples_error"] = str(exc)

    # Get plugins
    try:
        plugins_result = await _read_plugins(force_rescan=False, ctx=ctx)
        all_plugins = {p["name"].lower(): p for p in plugins_result.get("plugins", [])}
        suggested_plugin_names = genre_plugin_map.get(genre, [])

        for pname in suggested_plugin_names:
            if pname in all_plugins:
                result["plugins"].append(all_plugins[pname])
            else:
                result["plugins"].append({"name": pname, "installed": False, "note": "Not found in your setup"})
    except Exception as exc:
        result["plugins_error"] = str(exc)

    # Quick preset search for top plugin
    if result["plugins"] and result["plugins"][0].get("name"):
        top_plugin = result["plugins"][0]["name"]
        try:
            presets_result = await _find_presets(
                plugin_name=top_plugin,
                genre=genre,
                sound_type=element if element != "all" else None,
                free_only=True,
                ctx=ctx,
            )
            result["preset_suggestions"] = presets_result.get("presets", [])[:5]
        except Exception as exc:
            result["presets_error"] = str(exc)

    result["tips"] = genre_tips.get(genre, [
        f"Use a {genre} reference track to A/B check your mix.",
        "Study the drum pattern and groove feel of established {genre} producers.",
    ])

    return result


# ── Sample downloader tools ────────────────────────────────────────────────────

class FindSamplePacksInput(BaseModel):
    genre: str = Field(
        ...,
        description="Genre to search for (e.g. 'uk drill', 'trap', 'lo-fi', 'house', 'hip hop').",
        min_length=1,
    )
    style: Optional[str] = Field(
        None,
        description="Optional sub-style filter (e.g. 'dark', 'melodic', 'hard').",
    )


class DownloadSamplePackInput(BaseModel):
    url: str = Field(
        ...,
        description="Direct download URL for the sample pack (.zip) or individual audio file.",
        min_length=10,
    )
    pack_name: str = Field(
        ...,
        description="Name for the folder where the pack will be saved.",
        min_length=1,
    )
    destination_folder: Optional[str] = Field(
        None,
        description="Folder to save the pack into. Uses the first scan_folder from config if omitted.",
    )
    auto_scan: bool = Field(
        True,
        description="If True, automatically scan and classify the downloaded samples after extraction.",
    )


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def find_sample_packs(input: FindSamplePacksInput, ctx: Context) -> dict:
    """
    Search for free sample packs online matching a genre or style.

    Searches Looperman, SampleFocus, and a curated database of verified free packs.
    Returns a list with names, sources, URLs, and tags.
    Pass any result URL with direct=True to download_sample_pack to get it automatically.
    For results with direct=False, visit the URL in your browser to find the download button.
    """
    try:
        return await _find_sample_packs(
            genre=input.genre,
            style=input.style,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "find_sample_packs")


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def download_sample_pack(input: DownloadSamplePackInput, ctx: Context) -> dict:
    """
    Download a sample pack from a URL, extract it, and optionally scan the new samples.

    Handles .zip archives and individual audio files (.wav, .mp3, .flac, .ogg).
    Extracts all audio files into a sub-folder named after pack_name inside your samples folder.
    If auto_scan=True (default), immediately classifies all downloaded samples so they appear
    in get_samples queries.
    """
    try:
        return await _download_sample_pack(
            url=input.url,
            pack_name=input.pack_name,
            destination_folder=input.destination_folder,
            auto_scan=input.auto_scan,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "download_sample_pack")


# ── Freesound tools ────────────────────────────────────────────────────────────

class SearchFreesoundInput(BaseModel):
    genre: str = Field(
        ...,
        description="Genre to search (e.g. 'reggaeton', 'trap', 'lo-fi', 'uk drill').",
        min_length=1,
    )
    sound_type: Optional[str] = Field(
        None,
        description="Type of sound: kick, snare, hihat, loop, 808, bass, melody, etc.",
    )
    num_results: int = Field(
        10,
        ge=1,
        le=50,
        description="Number of results to return (max 50).",
    )


class DownloadFreesoundInput(BaseModel):
    preview_urls: List[str] = Field(
        ...,
        description="List of preview_url values from search_freesound results.",
        min_length=1,
    )
    pack_name: str = Field(
        ...,
        description="Folder name for the downloaded samples.",
        min_length=1,
    )
    destination_folder: Optional[str] = Field(
        None,
        description="Destination folder. Uses first scan_folder from config if omitted.",
    )
    auto_scan: bool = Field(
        True,
        description="Automatically scan and classify downloaded samples.",
    )


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def search_freesound(input: SearchFreesoundInput, ctx: Context) -> dict:
    """
    Search Freesound.org for free samples by genre using their public API.

    Returns a list of sounds with direct preview URLs (HQ 192kbps MP3).
    Pass the preview_url values to download_freesound_samples to download them automatically.

    Requires a free API key in config.json → freesound_api_key.
    Get one at https://freesound.org/apiv2/apply/ (instant, free).
    """
    try:
        return await _search_freesound(
            genre=input.genre,
            sound_type=input.sound_type,
            num_results=input.num_results,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "search_freesound")


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def download_freesound_samples(input: DownloadFreesoundInput, ctx: Context) -> dict:
    """
    Download Freesound preview files using direct URLs from search_freesound results.

    Downloads HQ 192kbps MP3 previews into a named folder in your samples directory.
    If auto_scan=True (default), immediately classifies all downloaded samples.

    The full workflow:
    1. search_freesound(genre='reggaeton') → get preview_urls
    2. download_freesound_samples(preview_urls=[...], pack_name='reggaeton pack')
    3. Samples appear in get_samples() automatically.
    """
    try:
        return await _download_freesound_samples(
            preview_urls=input.preview_urls,
            pack_name=input.pack_name,
            destination_folder=input.destination_folder,
            auto_scan=input.auto_scan,
            ctx=ctx,
        )
    except Exception as exc:
        return _handle_error(exc, "download_freesound_samples")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
