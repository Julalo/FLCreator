"""
freesound_downloader.py — search_freesound and download_freesound_samples tools.

Uses the Freesound.org API v2 which provides real direct download links.
Requires a free API key from https://freesound.org/apiv2/apply/
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import httpx
from fastmcp import Context

import config as cfg
from tools.sample_scanner import scan_samples as _scan_samples

FREESOUND_API = "https://freesound.org/apiv2"

# Genre → Freesound search tags/queries
_GENRE_QUERIES: dict[str, str] = {
    "reggaeton": "reggaeton dembow latin",
    "dembow": "dembow reggaeton",
    "latin": "latin percussion salsa",
    "trap": "trap 808 hihat",
    "uk drill": "uk drill bass",
    "drill": "drill bass kick",
    "lo-fi": "lofi vinyl jazz",
    "lofi": "lofi vinyl jazz",
    "house": "house kick clap",
    "hip hop": "hip hop boom bap",
    "edm": "edm synth drop",
    "dnb": "drum bass breakbeat",
    "techno": "techno kick industrial",
    "trance": "trance synth arpeggio",
    "ambient": "ambient pad atmosphere",
}

AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif"}


def _get_api_key() -> str | None:
    try:
        return cfg.get_config().get("freesound_api_key")
    except Exception:
        return None


async def search_freesound(
    genre: str,
    sound_type: Optional[str] = None,
    num_results: int = 10,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Search Freesound.org for free samples matching a genre.
    Returns results with preview URLs ready to pass to download_freesound_samples.
    """
    api_key = _get_api_key()
    if not api_key:
        return {
            "error": (
                "Freesound API key not configured. "
                "Get a free key at https://freesound.org/apiv2/apply/ "
                "then add it to config.json: {\"freesound_api_key\": \"your_key_here\"}"
            )
        }

    genre_lower = genre.lower().strip()
    query = _GENRE_QUERIES.get(genre_lower, genre)
    if sound_type:
        query += f" {sound_type}"

    params = {
        "query": query,
        "token": api_key,
        "fields": "id,name,tags,duration,type,previews,license,username",
        "filter": "duration:[0 TO 30]",  # max 30 seconds — keeps it to one-shots and short loops
        "page_size": min(num_results, 50),
        "sort": "downloads_desc",
    }

    if ctx:
        await ctx.info(f"Searching Freesound for '{query}'...")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{FREESOUND_API}/search/text/", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        return {"error": f"Freesound API error: {exc}"}

    sounds = data.get("results", [])
    results = []

    for s in sounds:
        previews = s.get("previews", {})
        # HQ preview is 192kbps MP3 — fully usable for production
        preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")

        results.append({
            "id": s.get("id"),
            "name": s.get("name", "Unknown"),
            "username": s.get("username"),
            "duration": round(s.get("duration", 0), 2),
            "type": s.get("type"),
            "tags": s.get("tags", [])[:8],
            "license": s.get("license"),
            "preview_url": preview_url,
            "page_url": f"https://freesound.org/s/{s.get('id')}/",
        })

    if ctx:
        await ctx.info(f"Found {len(results)} sounds on Freesound for '{genre}'.")

    return {
        "genre": genre,
        "query_used": query,
        "count": len(results),
        "sounds": results,
        "tip": (
            "Pass preview_url values to download_freesound_samples to download them. "
            "These are HQ previews (192kbps MP3) — free to use under their respective licenses."
        ),
    }


async def download_freesound_samples(
    preview_urls: list[str],
    pack_name: str,
    destination_folder: Optional[str] = None,
    auto_scan: bool = True,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Download Freesound preview files (direct MP3 links) into a local folder
    and optionally scan them into the sample library.

    preview_urls: list of preview_url values from search_freesound results.
    """
    if not preview_urls:
        return {"error": "No preview URLs provided."}

    api_key = _get_api_key()
    if not api_key:
        return {
            "error": (
                "Freesound API key not configured. "
                "Add it to config.json: {\"freesound_api_key\": \"your_key_here\"}"
            )
        }

    # Resolve destination folder
    if destination_folder:
        dest = Path(destination_folder)
    else:
        scan_folders = cfg.sample_scan_folders()
        dest = scan_folders[0] if scan_folders else Path.home() / "Music" / "Samples"

    pack_folder = dest / pack_name
    pack_folder.mkdir(parents=True, exist_ok=True)

    downloaded: list[str] = []
    failed: list[str] = []

    headers = {
        "User-Agent": "FL-Studio-Producer-Brain/1.0",
        "Authorization": f"Token {api_key}",
    }

    if ctx:
        await ctx.info(f"Downloading {len(preview_urls)} samples to {pack_folder}...")

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        for i, url in enumerate(preview_urls):
            try:
                resp = await client.get(url)
                resp.raise_for_status()

                # Derive filename from URL
                url_path = Path(url.split("?")[0])
                ext = url_path.suffix.lower() or ".mp3"
                stem = url_path.stem or f"freesound_{i+1}"

                dest_file = pack_folder / f"{stem}{ext}"
                counter = 1
                while dest_file.exists():
                    dest_file = pack_folder / f"{stem}_{counter}{ext}"
                    counter += 1

                dest_file.write_bytes(resp.content)
                downloaded.append(str(dest_file))

                if ctx:
                    await ctx.info(f"[{i+1}/{len(preview_urls)}] Downloaded: {dest_file.name}")

            except Exception as exc:
                failed.append(f"{url}: {exc}")
                if ctx:
                    await ctx.error(f"Failed to download {url}: {exc}")

    scan_result = None
    if auto_scan and downloaded:
        if ctx:
            await ctx.info("Scanning downloaded samples...")
        scan_result = await _scan_samples(
            folder_path=str(pack_folder),
            force_rescan=True,
            ctx=ctx,
        )

    return {
        "success": len(downloaded) > 0,
        "pack_name": pack_name,
        "pack_folder": str(pack_folder),
        "downloaded": len(downloaded),
        "failed": len(failed),
        "files": downloaded,
        "errors": failed if failed else None,
        "scan_result": scan_result,
    }
