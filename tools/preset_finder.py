"""
preset_finder.py — find_presets MCP tool.
Searches preset websites for free presets matching plugin + genre + sound type.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlencode, quote_plus

import httpx
from fastmcp import Context

from models import Preset

# Genre → keyword aliases to broaden search
GENRE_ALIASES: dict[str, list[str]] = {
    "trap": ["trap", "hi-hat", "808"],
    "drill": ["drill", "uk drill"],
    "uk_drill": ["uk drill", "drill"],
    "house": ["house", "deep house"],
    "lo-fi": ["lo-fi", "lofi", "chill"],
    "lofi": ["lo-fi", "lofi", "chill"],
    "edm": ["edm", "electronic", "festival"],
    "future_bass": ["future bass", "future"],
    "dubstep": ["dubstep", "bass music"],
    "dnb": ["drum and bass", "dnb"],
    "hip_hop": ["hip hop", "boom bap"],
    "pop": ["pop", "mainstream"],
    "ambient": ["ambient", "atmospheric"],
    "techno": ["techno", "industrial"],
    "trance": ["trance", "progressive"],
}

# Search source definitions: (name, search_url_template)
# {query} = URL-encoded search string
_SOURCES = [
    (
        "Preset Share",
        "https://presetshare.com/?s={query}",
    ),
    (
        "ADSR Sounds (free)",
        "https://www.adsrsounds.com/product-type/presets/?free=true&search={query}",
    ),
    (
        "Splice (free tier)",
        "https://splice.com/sounds/search?q={query}&is_free=true",
    ),
]

# Plugin-specific manufacturer pages
_MANUFACTURER_URLS: dict[str, str] = {
    "serum": "https://xferrecords.com/freeware",
    "massive": "https://www.native-instruments.com/en/specials/free-tools/",
    "vital": "https://vital.audio/#getvital",
    "sylenth1": "https://www.lennardigital.com/sylenth1/",
}


async def _search_source(
    client: httpx.AsyncClient,
    source_name: str,
    url: str,
) -> list[dict]:
    """Attempt a simple HTTP GET and parse <a> hrefs + titles as preset candidates."""
    results: list[dict] = []
    try:
        resp = await client.get(url, timeout=12.0, follow_redirects=True)
        if resp.status_code != 200:
            return results

        text = resp.text

        # Very lightweight HTML scrape: extract links with preset-like text
        # Pattern: <a href="...">[text]</a>
        link_pattern = re.compile(
            r'<a\s+[^>]*href="([^"]+)"[^>]*>([^<]{5,120})</a>',
            re.I | re.S,
        )
        for href, link_text in link_pattern.findall(text):
            link_text = re.sub(r"\s+", " ", link_text).strip()
            if any(skip in href.lower() for skip in ["javascript:", "mailto:", "#"]):
                continue
            # Only keep links that look like preset/download pages
            if not any(kw in href.lower() for kw in ["preset", "download", "free", "sounds", "patch"]):
                continue
            results.append({
                "name": link_text,
                "source": source_name,
                "url": href if href.startswith("http") else None,
                "description": None,
                "genre_tags": [],
                "sound_type": None,
                "free": True,
                "local_path": None,
                "installed": False,
            })
            if len(results) >= 5:
                break
    except Exception:
        pass

    return results


async def find_presets(
    plugin_name: str,
    genre: str,
    sound_type: Optional[str] = None,
    free_only: bool = True,
    ctx: Optional[Context] = None,
) -> dict:
    genre_lower = genre.lower().replace(" ", "_")
    keywords = GENRE_ALIASES.get(genre_lower, [genre])

    base_query = f"{plugin_name} presets {' '.join(keywords)}"
    if sound_type:
        base_query += f" {sound_type}"
    if free_only:
        base_query += " free"

    encoded = quote_plus(base_query)

    all_results: list[dict] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "FL-Studio-Producer-Brain/1.0 (preset research tool)"},
        follow_redirects=True,
    ) as client:
        for source_name, url_template in _SOURCES:
            url = url_template.format(query=encoded)
            if ctx:
                await ctx.info(f"Searching {source_name}...")
            found = await _search_source(client, source_name, url)
            # Enrich with genre/plugin context
            for item in found:
                item["plugin_name"] = plugin_name
                item["genre_tags"] = keywords
                item["sound_type"] = sound_type
            all_results.extend(found)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for item in all_results:
        url_key = item.get("url") or item["name"]
        if url_key not in seen_urls:
            seen_urls.add(url_key)
            unique.append(item)

    # Add manufacturer page as always-available fallback
    mfg_url = _MANUFACTURER_URLS.get(plugin_name.lower())
    if mfg_url:
        unique.append({
            "name": f"{plugin_name} Official Freeware / Presets Page",
            "plugin_name": plugin_name,
            "source": "Official",
            "url": mfg_url,
            "description": "Check the official page for free presets and patches.",
            "genre_tags": keywords,
            "sound_type": sound_type,
            "free": True,
            "local_path": None,
            "installed": False,
        })

    if ctx:
        await ctx.info(f"Found {len(unique)} preset results for {plugin_name} / {genre}.")

    return {
        "query": {
            "plugin_name": plugin_name,
            "genre": genre,
            "sound_type": sound_type,
            "free_only": free_only,
        },
        "count": len(unique),
        "presets": unique,
    }
