"""
plugin_researcher.py — research_plugin MCP tool.
Fetches plugin info from the web and caches it in plugins_library.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import httpx
from fastmcp import Context

import config as cfg

CACHE_FILE = "plugins_library.json"

# Known plugin database (avoids unnecessary HTTP calls for common plugins)
_KNOWN_PLUGINS: dict[str, dict] = {
    "serum": {
        "synthesis_type": "wavetable",
        "recommended_genres": ["edm", "dubstep", "future bass", "trap", "pop", "house"],
        "sound_types": ["lead", "bass", "pad", "pluck", "arp", "sfx"],
        "description": "Xfer Records Serum — industry-standard wavetable synthesizer with a visual wavetable editor, drag-and-drop modulation, and high-quality built-in effects chain.",
        "useful_links": [
            "https://xferrecords.com/products/serum",
            "https://forum.xferrecords.com",
        ],
    },
    "massive": {
        "synthesis_type": "wavetable",
        "recommended_genres": ["dubstep", "drum and bass", "techno", "trap"],
        "sound_types": ["bass", "lead", "pad", "sfx"],
        "description": "Native Instruments Massive — classic wavetable synth known for heavy basses and aggressive leads.",
        "useful_links": ["https://www.native-instruments.com/en/products/komplete/synths/massive/"],
    },
    "massive x": {
        "synthesis_type": "wavetable",
        "recommended_genres": ["electronic", "techno", "cinematic", "trap"],
        "sound_types": ["bass", "lead", "pad", "texture"],
        "description": "Native Instruments Massive X — next-gen wavetable synth with dual wavetable oscillators and advanced modulation.",
        "useful_links": ["https://www.native-instruments.com/en/products/komplete/synths/massive-x/"],
    },
    "sylenth1": {
        "synthesis_type": "virtual analog",
        "recommended_genres": ["trance", "house", "edm", "pop"],
        "sound_types": ["lead", "pad", "bass", "supersaw"],
        "description": "LennarDigital Sylenth1 — warm virtual analog synth loved for its classic supersaw pads and smooth basses.",
        "useful_links": ["https://www.lennardigital.com/sylenth1/"],
    },
    "kontakt": {
        "synthesis_type": "sampler",
        "recommended_genres": ["cinematic", "orchestral", "hip hop", "lo-fi"],
        "sound_types": ["strings", "brass", "keys", "drums", "ethnic"],
        "description": "Native Instruments Kontakt — the industry standard sampler with thousands of third-party libraries.",
        "useful_links": ["https://www.native-instruments.com/en/products/komplete/samplers/kontakt-7/"],
    },
    "vital": {
        "synthesis_type": "wavetable",
        "recommended_genres": ["edm", "future bass", "lo-fi", "pop", "trap"],
        "sound_types": ["lead", "bass", "pad", "pluck"],
        "description": "Vital — free/paid wavetable synthesizer with spectral morphing and a powerful modulation matrix.",
        "useful_links": ["https://vital.audio/"],
    },
    "omnisphere": {
        "synthesis_type": "hybrid (sample + synthesis)",
        "recommended_genres": ["cinematic", "pop", "electronic", "ambient"],
        "sound_types": ["pad", "texture", "lead", "keys", "bass"],
        "description": "Spectrasonics Omnisphere — flagship hybrid synth combining a massive sample library with synthesis engines.",
        "useful_links": ["https://www.spectrasonics.net/products/omnisphere/"],
    },
    "nexus": {
        "synthesis_type": "rompler",
        "recommended_genres": ["trance", "pop", "dance", "edm"],
        "sound_types": ["lead", "pad", "bass", "arp", "brass"],
        "description": "reFX Nexus — rompler with a huge built-in library of EDM-focused presets.",
        "useful_links": ["https://refx.com/nexus/"],
    },
    "3xosc": {
        "synthesis_type": "virtual analog",
        "recommended_genres": ["any"],
        "sound_types": ["bass", "lead", "pad", "sub"],
        "description": "FL Studio native 3x Osc — simple but versatile oscillator-based synth. Great for sub basses and basic leads.",
        "useful_links": ["https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/3xOsc.htm"],
    },
    "harmor": {
        "synthesis_type": "additive / resynthesis",
        "recommended_genres": ["edm", "cinematic", "experimental"],
        "sound_types": ["pad", "texture", "lead", "bass"],
        "description": "FL Studio native Harmor — additive synthesizer with image-to-sound resynthesis capabilities.",
        "useful_links": ["https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Harmor.htm"],
    },
}


def _cache_path() -> Path:
    return cfg.cache_folder() / CACHE_FILE


def _load_cache() -> dict[str, dict]:
    p = _cache_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(data: dict[str, dict]) -> None:
    _cache_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


async def _fetch_plugin_info_web(plugin_name: str) -> dict:
    """Try to scrape basic plugin info. Returns a partial dict or empty."""
    results: dict = {
        "synthesis_type": None,
        "recommended_genres": [],
        "sound_types": [],
        "description": None,
        "useful_links": [],
    }

    search_url = f"https://en.wikipedia.org/w/api.php"
    params = {
        "action": "opensearch",
        "search": f"{plugin_name} synthesizer plugin",
        "limit": 3,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(search_url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) >= 4 and data[1]:
                    results["description"] = data[2][0] if data[2] else None
                    results["useful_links"] = list(data[3][:2]) if data[3] else []
    except Exception:
        pass

    return results


async def research_plugin(
    plugin_name: str,
    ctx: Optional[Context] = None,
) -> dict:
    cache = _load_cache()
    name_key = plugin_name.lower()

    # Check if already researched
    if name_key in cache and cache[name_key].get("researched"):
        if ctx:
            await ctx.log_info(f"Returning cached research for '{plugin_name}'")
        return {"plugin": cache[name_key], "source": "cache"}

    # Check built-in knowledge base first
    known = _KNOWN_PLUGINS.get(name_key)
    if known:
        if ctx:
            await ctx.log_info(f"Found '{plugin_name}' in built-in knowledge base.")
        plugin_data = cache.get(name_key, {"name": plugin_name})
        plugin_data.update(known)
        plugin_data["researched"] = True
        cache[name_key] = plugin_data
        _save_cache(cache)
        return {"plugin": plugin_data, "source": "built-in"}

    # Web fetch as fallback
    if ctx:
        await ctx.log_info(f"Fetching online info for '{plugin_name}'...")

    web_info = await _fetch_plugin_info_web(plugin_name)

    plugin_data = cache.get(name_key, {"name": plugin_name})
    plugin_data.update(web_info)
    plugin_data["researched"] = True
    cache[name_key] = plugin_data
    _save_cache(cache)

    if ctx:
        await ctx.log_info(f"Research complete for '{plugin_name}'.")

    return {"plugin": plugin_data, "source": "web"}
