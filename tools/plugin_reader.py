"""
plugin_reader.py — read_plugins MCP tool.
Reads FL Studio plugin database and system VST folders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastmcp import Context

import config as cfg
from models import Plugin, PluginType

CACHE_FILE = "plugins_library.json"


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


def _parse_nfo(nfo_path: Path) -> dict[str, str]:
    """Parse a simple key=value .nfo file."""
    data: dict[str, str] = {}
    try:
        for line in nfo_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                data[k.strip().lower()] = v.strip()
    except Exception:
        pass
    return data


def _scan_fl_db(db_folder: Path, plugin_type: PluginType) -> list[dict]:
    plugins: list[dict] = []
    if not db_folder.exists():
        return plugins

    for nfo_file in db_folder.rglob("*.nfo"):
        nfo_data = _parse_nfo(nfo_file)
        name = nfo_data.get("name") or nfo_file.stem
        vendor = nfo_data.get("vendor") or nfo_data.get("manufacturer") or None
        plugin_path = nfo_data.get("pluginpath") or None

        plugins.append({
            "name": name,
            "vendor": vendor,
            "type": plugin_type.value,
            "path": plugin_path,
            "nfo_path": str(nfo_file),
            "synthesis_type": None,
            "recommended_genres": [],
            "sound_types": [],
            "description": None,
            "useful_links": [],
            "researched": False,
        })

    return plugins


def _scan_vst_folder(vst_folder: Path) -> list[dict]:
    """Scan a VST/VST3 directory for DLL / VST3 bundles."""
    plugins: list[dict] = []
    if not vst_folder.exists():
        return plugins

    exts = {".dll", ".vst3"}
    for f in vst_folder.rglob("*"):
        if f.suffix.lower() in exts and f.is_file():
            plugins.append({
                "name": f.stem,
                "vendor": None,
                "type": PluginType.unknown.value,
                "path": str(f),
                "nfo_path": None,
                "synthesis_type": None,
                "recommended_genres": [],
                "sound_types": [],
                "description": None,
                "useful_links": [],
                "researched": False,
            })

    return plugins


async def read_plugins(
    force_rescan: bool = False,
    ctx: Optional[Context] = None,
) -> dict:
    if not force_rescan:
        cache = _load_cache()
        if cache:
            if ctx:
                await ctx.log_info(f"Returning {len(cache)} plugins from cache.")
            by_type: dict[str, int] = {}
            for v in cache.values():
                t = v.get("type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1
            return {
                "count": len(cache),
                "breakdown_by_type": by_type,
                "plugins": list(cache.values()),
            }

    if ctx:
        await ctx.log_info("Scanning FL Studio plugin database and VST folders...")

    all_plugins: list[dict] = []

    # FL Studio database
    all_plugins += _scan_fl_db(cfg.plugins_db_generators(), PluginType.generator)
    all_plugins += _scan_fl_db(cfg.plugins_db_effects(), PluginType.effect)

    # System VST folders
    for vst_dir in cfg.vst_folders():
        all_plugins += _scan_vst_folder(vst_dir)

    # Deduplicate by name (FL DB takes priority)
    seen: dict[str, dict] = {}
    for p in all_plugins:
        key = p["name"].lower()
        if key not in seen or p.get("nfo_path"):
            seen[key] = p

    cache_data: dict[str, dict] = {p["name"]: p for p in seen.values()}
    _save_cache(cache_data)

    if ctx:
        await ctx.log_info(f"Found {len(cache_data)} unique plugins.")

    by_type = {}
    for v in cache_data.values():
        t = v.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "count": len(cache_data),
        "breakdown_by_type": by_type,
        "plugins": list(cache_data.values()),
    }
