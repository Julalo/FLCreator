"""
sample_downloader.py — find_sample_packs and download_sample_pack MCP tools.
Searches free sample pack sites and downloads + extracts packs automatically.
"""

from __future__ import annotations

import re
import zipfile
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import httpx
from fastmcp import Context

import config as cfg
from tools.sample_scanner import scan_samples as _scan_samples

# ── Curated free pack database by genre ──────────────────────────────────────
# These are verified free/royalty-free direct download links.
# Format: {genre: [{name, url, source, description, tags}]}

_CURATED_PACKS: dict[str, list[dict]] = {
    "uk drill": [
        {
            "name": "Cymatics Lethal UK Drill Sample Pack (Free)",
            "source": "Cymatics",
            "url": "https://cymatics.fm/pages/free-download-vault",
            "description": "Dark 808s, rolling hi-hats, and minor key melodies typical of UK drill.",
            "tags": ["uk drill", "808", "hihat", "dark"],
            "direct": False,
        },
        {
            "name": "Looperman UK Drill Loops",
            "source": "Looperman",
            "url": "https://www.looperman.com/loops/search?term=uk+drill&free=1",
            "description": "Community-uploaded UK drill loops, royalty-free.",
            "tags": ["uk drill", "loop", "free"],
            "direct": False,
        },
    ],
    "drill": [
        {
            "name": "Drill Sample Pack — Looperman",
            "source": "Looperman",
            "url": "https://www.looperman.com/loops/search?term=drill&free=1",
            "description": "Drill loops and one-shots, royalty-free.",
            "tags": ["drill", "loop", "808"],
            "direct": False,
        },
    ],
    "trap": [
        {
            "name": "Cymatics Nova Trap Sample Pack (Free)",
            "source": "Cymatics",
            "url": "https://cymatics.fm/pages/free-download-vault",
            "description": "Trap drums, 808s, hi-hat patterns and dark melodies.",
            "tags": ["trap", "808", "hihat", "drums"],
            "direct": False,
        },
        {
            "name": "Looperman Trap Loops",
            "source": "Looperman",
            "url": "https://www.looperman.com/loops/search?term=trap&free=1",
            "description": "Trap loops and samples, royalty-free.",
            "tags": ["trap", "loop", "free"],
            "direct": False,
        },
    ],
    "lo-fi": [
        {
            "name": "Looperman Lo-Fi Loops",
            "source": "Looperman",
            "url": "https://www.looperman.com/loops/search?term=lofi&free=1",
            "description": "Lo-fi drums, jazz chords, vinyl textures.",
            "tags": ["lo-fi", "lofi", "chill", "jazz"],
            "direct": False,
        },
        {
            "name": "SampleFocus Lo-Fi Samples",
            "source": "SampleFocus",
            "url": "https://samplefocus.com/tag/lo-fi",
            "description": "Individual lo-fi samples, free to download.",
            "tags": ["lo-fi", "one-shot", "free"],
            "direct": False,
        },
    ],
    "house": [
        {
            "name": "Looperman House Loops",
            "source": "Looperman",
            "url": "https://www.looperman.com/loops/search?term=house&free=1",
            "description": "House music loops, chord stabs, four-on-the-floor grooves.",
            "tags": ["house", "loop", "chords"],
            "direct": False,
        },
    ],
    "hip hop": [
        {
            "name": "Looperman Hip Hop Loops",
            "source": "Looperman",
            "url": "https://www.looperman.com/loops/search?term=hip+hop&free=1",
            "description": "Hip hop drums, boom bap loops, samples.",
            "tags": ["hip hop", "boom bap", "loop"],
            "direct": False,
        },
    ],
    "edm": [
        {
            "name": "Looperman EDM Loops",
            "source": "Looperman",
            "url": "https://www.looperman.com/loops/search?term=edm&free=1",
            "description": "EDM drops, synth loops, festival-ready sounds.",
            "tags": ["edm", "loop", "synth"],
            "direct": False,
        },
    ],
}

_GENRE_ALIASES: dict[str, str] = {
    "lofi": "lo-fi",
    "uk_drill": "uk drill",
    "hiphop": "hip hop",
    "boom bap": "hip hop",
    "dnb": "drum and bass",
    "d&b": "drum and bass",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


async def _scrape_looperman(genre: str, client: httpx.AsyncClient) -> list[dict]:
    """Scrape Looperman search results for free loops."""
    results = []
    url = f"https://www.looperman.com/loops/search?term={quote_plus(genre)}&free=1"
    try:
        resp = await client.get(url, timeout=12.0)
        if resp.status_code != 200:
            return results

        text = resp.text
        # Extract loop entries — Looperman wraps each loop in a div with class "loop"
        # We look for download links with .wav or .mp3
        dl_pattern = re.compile(
            r'href="(https://www\.looperman\.com/media/[^"]+\.(?:wav|mp3))"',
            re.I
        )
        name_pattern = re.compile(
            r'class="loop-title"[^>]*>\s*<a[^>]*>([^<]+)</a>',
            re.I
        )

        names = name_pattern.findall(text)
        dls = dl_pattern.findall(text)

        for i, dl_url in enumerate(dls[:8]):
            name = names[i].strip() if i < len(names) else f"{genre} loop {i+1}"
            results.append({
                "name": name,
                "source": "Looperman",
                "url": dl_url,
                "description": f"Free {genre} loop from Looperman (royalty-free).",
                "tags": [genre, "loop", "free"],
                "direct": True,
                "extension": Path(dl_url).suffix.lower(),
            })
    except Exception:
        pass
    return results


async def _scrape_samplefocus(genre: str, client: httpx.AsyncClient) -> list[dict]:
    """Scrape SampleFocus for individual free samples."""
    results = []
    url = f"https://samplefocus.com/samples?q={quote_plus(genre)}"
    try:
        resp = await client.get(url, timeout=12.0)
        if resp.status_code != 200:
            return results

        text = resp.text
        # SampleFocus lists samples with their download links
        dl_pattern = re.compile(
            r'"download_url"\s*:\s*"([^"]+)"',
            re.I
        )
        name_pattern = re.compile(
            r'"name"\s*:\s*"([^"]+)"',
            re.I
        )

        names = name_pattern.findall(text)
        dls = dl_pattern.findall(text)

        for i, dl_url in enumerate(dls[:8]):
            name = names[i].strip() if i < len(names) else f"{genre} sample {i+1}"
            if not dl_url.startswith("http"):
                dl_url = "https://samplefocus.com" + dl_url
            results.append({
                "name": name,
                "source": "SampleFocus",
                "url": dl_url,
                "description": f"Free {genre} sample from SampleFocus.",
                "tags": [genre, "free"],
                "direct": True,
                "extension": ".wav",
            })
    except Exception:
        pass
    return results


async def find_sample_packs(
    genre: str,
    style: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Search for free sample packs matching a genre/style.
    Returns a list of packs with download links.
    """
    genre_lower = genre.lower().strip()
    genre_lower = _GENRE_ALIASES.get(genre_lower, genre_lower)

    results: list[dict] = []

    # Add curated packs first
    curated = _CURATED_PACKS.get(genre_lower, [])
    results.extend(curated)

    # Also check partial matches
    for key, packs in _CURATED_PACKS.items():
        if genre_lower in key or key in genre_lower:
            for p in packs:
                if p not in results:
                    results.append(p)

    # Live scraping
    if ctx:
        await ctx.log_info(f"Scraping Looperman and SampleFocus for '{genre}'...")

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        looperman = await _scrape_looperman(genre_lower, client)
        samplefocus = await _scrape_samplefocus(genre_lower, client)

    results.extend(looperman)
    results.extend(samplefocus)

    # Filter by style if provided
    if style:
        style_lower = style.lower()
        styled = [r for r in results if style_lower in " ".join(r.get("tags", [])).lower()]
        if styled:
            results = styled

    # Deduplicate by URL
    seen: set[str] = set()
    unique = []
    for r in results:
        key = r.get("url", r["name"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    if ctx:
        await ctx.log_info(f"Found {len(unique)} sample packs/files for '{genre}'.")

    return {
        "genre": genre,
        "style": style,
        "count": len(unique),
        "packs": unique,
        "tip": (
            "Pass the URL of any result with direct=True to download_sample_pack. "
            "For results with direct=False, visit the URL to find the download button."
        ),
    }


async def download_sample_pack(
    url: str,
    pack_name: str,
    destination_folder: Optional[str] = None,
    auto_scan: bool = True,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Download a sample pack (zip or individual audio file) from a URL,
    extract it into the destination folder, and optionally scan the new samples.
    """
    # Resolve destination
    if destination_folder:
        dest = Path(destination_folder)
    else:
        scan_folders = cfg.sample_scan_folders()
        dest = scan_folders[0] if scan_folders else Path.home() / "Music" / "Samples"

    pack_folder = dest / pack_name
    pack_folder.mkdir(parents=True, exist_ok=True)

    if ctx:
        await ctx.log_info(f"Downloading from {url} ...")

    # Download
    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            follow_redirects=True,
            timeout=60.0,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as exc:
        return {"error": f"Download failed: {exc}", "url": url}

    content = resp.content
    content_type = resp.headers.get("content-type", "")

    # Determine file type
    url_clean = url.split("?")[0]
    ext = Path(url_clean).suffix.lower()
    if not ext:
        if "zip" in content_type:
            ext = ".zip"
        elif "wav" in content_type or "wave" in content_type:
            ext = ".wav"
        elif "mpeg" in content_type or "mp3" in content_type:
            ext = ".mp3"
        else:
            ext = ".zip"  # assume zip if unknown

    AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif"}
    extracted_files: list[str] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = Path(tmpdir) / f"download{ext}"
        tmp_file.write_bytes(content)

        if ext == ".zip":
            if ctx:
                await ctx.log_info("Extracting zip archive...")
            try:
                with zipfile.ZipFile(tmp_file, "r") as zf:
                    zf.extractall(tmpdir)
            except zipfile.BadZipFile:
                return {
                    "error": "Downloaded file is not a valid zip. The URL may require login or redirect to a page.",
                    "url": url,
                    "suggestion": "Visit the URL in your browser to download manually.",
                }

            # Copy audio files to pack folder
            for audio in Path(tmpdir).rglob("*"):
                if audio.suffix.lower() in AUDIO_EXTS and audio.is_file():
                    dest_file = pack_folder / audio.name
                    counter = 1
                    while dest_file.exists():
                        dest_file = pack_folder / f"{audio.stem}_{counter}{audio.suffix}"
                        counter += 1
                    shutil.copy2(str(audio), str(dest_file))
                    extracted_files.append(str(dest_file))

        elif ext in AUDIO_EXTS:
            # Single audio file
            dest_file = pack_folder / f"{pack_name}{ext}"
            shutil.copy2(str(tmp_file), str(dest_file))
            extracted_files.append(str(dest_file))
        else:
            return {
                "error": f"Unknown file type: {ext}. Expected .zip or audio file.",
                "url": url,
            }

    if not extracted_files:
        return {
            "error": "No audio files found in the downloaded content.",
            "url": url,
            "pack_folder": str(pack_folder),
        }

    if ctx:
        await ctx.log_info(f"Extracted {len(extracted_files)} audio files to {pack_folder}")

    # Auto-scan the new samples
    scan_result = None
    if auto_scan:
        if ctx:
            await ctx.log_info("Scanning new samples...")
        scan_result = await _scan_samples(
            folder_path=str(pack_folder),
            force_rescan=True,
            ctx=ctx,
        )

    return {
        "success": True,
        "pack_name": pack_name,
        "pack_folder": str(pack_folder),
        "files_downloaded": len(extracted_files),
        "files": extracted_files[:20],  # cap list for readability
        "scan_result": scan_result,
    }
