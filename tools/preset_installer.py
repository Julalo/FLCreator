"""
preset_installer.py — install_preset and load_preset_in_fl MCP tools.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional

import httpx
from fastmcp import Context

import config as cfg

CACHE_FILE = "presets_cache.json"
PRESET_EXTS = {".fst", ".fxp", ".fxb"}

# Map plugin names to their native preset folder (relative to user docs or absolute)
_PLUGIN_PRESET_DIRS: dict[str, str] = {
    "serum": r"Xfer\Serum Presets\Presets",
    "serum 2": r"Xfer\Serum2 Presets\Presets",
    "vital": r"Vital\presets",
    "kontakt": r"Native Instruments\User Content\Kontakt",
    "massive": r"Native Instruments\Massive\Sounds\User",
    "massive x": r"Native Instruments\Massive X\Presets\User",
    "sylenth1": r"LennarDigital\Sylenth1\Presets",
}


def _cache_path() -> Path:
    return cfg.cache_folder() / CACHE_FILE


def _load_presets_cache() -> dict[str, dict]:
    p = _cache_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_presets_cache(data: dict[str, dict]) -> None:
    _cache_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _resolve_install_dir(plugin_name: str, file_ext: str) -> Path:
    """Determine where to install the preset file."""
    name_lower = plugin_name.lower()

    # Plugin-native preset folder (relative to Documents)
    native_rel = _PLUGIN_PRESET_DIRS.get(name_lower)
    if native_rel:
        docs = Path.home() / "Documents"
        target = docs / native_rel
        target.mkdir(parents=True, exist_ok=True)
        return target

    # Default to FL Studio plugin database folder
    if file_ext in {".fst"}:
        target = cfg.fl_presets_generators() / plugin_name
    else:
        target = cfg.fl_presets_generators() / plugin_name

    target.mkdir(parents=True, exist_ok=True)
    return target


async def install_preset(
    preset_url: str,
    plugin_name: str,
    preset_name: str,
    ctx: Optional[Context] = None,
) -> dict:
    if ctx:
        await ctx.log_info(f"Downloading preset from {preset_url} ...")

    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "FL-Studio-Producer-Brain/1.0"},
        ) as client:
            resp = await client.get(preset_url)
            resp.raise_for_status()
    except Exception as exc:
        return {"error": f"Download failed: {exc}", "url": preset_url}

    content = resp.content
    content_type = resp.headers.get("content-type", "")

    # Determine file extension from URL or content-type
    url_path = Path(preset_url.split("?")[0])
    ext = url_path.suffix.lower()
    if not ext:
        ext = ".bin"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / f"preset{ext}"
        tmp_path.write_bytes(content)

        preset_files: list[Path] = []

        if ext == ".zip" or "zip" in content_type:
            if ctx:
                await ctx.log_info("Extracting zip archive...")
            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(tmpdir)
            preset_files = [
                p for p in Path(tmpdir).rglob("*")
                if p.suffix.lower() in PRESET_EXTS and p.is_file()
            ]
        elif ext in PRESET_EXTS:
            preset_files = [tmp_path]
        else:
            return {
                "error": f"Unknown preset format: {ext}. Expected .fst, .fxp, .fxb, or .zip",
                "url": preset_url,
            }

        if not preset_files:
            return {
                "error": "No preset files (.fst/.fxp/.fxb) found in the download.",
                "url": preset_url,
            }

        installed: list[str] = []
        install_dir = _resolve_install_dir(plugin_name, preset_files[0].suffix.lower())

        for pf in preset_files:
            dest = install_dir / pf.name
            # Avoid overwriting with a suffix
            counter = 1
            while dest.exists():
                dest = install_dir / f"{pf.stem}_{counter}{pf.suffix}"
                counter += 1
            shutil.copy2(str(pf), str(dest))
            installed.append(str(dest))

            if ctx:
                await ctx.log_info(f"Installed: {dest}")

    # Register in cache
    presets_cache = _load_presets_cache()
    cache_key = f"{plugin_name.lower()}_{preset_name}"
    presets_cache[cache_key] = {
        "name": preset_name,
        "plugin_name": plugin_name,
        "url": preset_url,
        "local_paths": installed,
        "installed": True,
    }
    _save_presets_cache(presets_cache)

    return {
        "success": True,
        "preset_name": preset_name,
        "plugin_name": plugin_name,
        "installed_files": installed,
        "install_dir": str(install_dir),
    }


async def load_preset_in_fl(
    preset_path: str,
    channel_index: Optional[int] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """Load a .fst preset into FL Studio via pyautogui UI automation."""
    preset = Path(preset_path)
    if not preset.exists():
        return {"error": f"Preset file not found: {preset_path}"}

    try:
        import pygetwindow as gw  # type: ignore
    except ImportError:
        return {
            "error": "pygetwindow is not installed. Run: pip install pygetwindow",
            "preset_path": preset_path,
        }

    try:
        import pyautogui  # type: ignore
    except ImportError:
        return {
            "error": "pyautogui is not installed. Run: pip install pyautogui",
            "preset_path": preset_path,
        }

    # Find FL Studio window
    fl_windows = [w for w in gw.getAllWindows() if "FL Studio" in w.title]
    if not fl_windows:
        return {
            "error": "FL Studio is not open. Please launch FL Studio first.",
        }

    fl_win = fl_windows[0]
    if ctx:
        await ctx.log_info(f"Found FL Studio window: '{fl_win.title}'")

    try:
        fl_win.activate()
        time.sleep(0.5)
    except Exception as exc:
        if ctx:
            await ctx.log_error(f"Could not activate FL Studio window: {exc}")

    try:
        # Open FL Studio browser with F8
        pyautogui.hotkey("f8")
        time.sleep(0.8)

        # Get FL window position and size for drag target
        fl_left = fl_win.left
        fl_top = fl_win.top
        fl_width = fl_win.width
        fl_height = fl_win.height

        # Channel rack is typically in the lower-left region of FL
        if channel_index is not None:
            channel_y = fl_top + 150 + (channel_index * 20)
            drop_x = fl_left + 250
            drop_y = min(channel_y, fl_top + fl_height - 50)
        else:
            drop_x = fl_left + 250
            drop_y = fl_top + 200

        # Drag the preset file to FL Studio
        # This works best when FL browser is open and the preset is visible
        pyautogui.moveTo(drop_x, drop_y, duration=0.3)
        time.sleep(0.2)

        if ctx:
            await ctx.log_info(
                f"UI automation: attempted to open browser (F8) and position cursor at "
                f"({drop_x}, {drop_y}). Manual drag may be required."
            )

        return {
            "success": True,
            "message": (
                "FL Studio browser opened (F8). "
                "The preset was not auto-dragged — navigate to the preset in the FL browser "
                f"({preset.parent}) and drag '{preset.name}' to the channel rack manually, "
                "or double-click it to load it."
            ),
            "preset_path": preset_path,
            "fl_window": fl_win.title,
            "note": (
                "Full drag-and-drop automation requires FL Studio to be in windowed mode "
                "and the browser to show the preset folder. "
                "Alternatively, use the FL browser (F8) to navigate to the preset folder."
            ),
        }

    except Exception as exc:
        if ctx:
            await ctx.log_error(f"UI automation failed: {exc}")
        return {
            "error": f"pyautogui automation failed: {exc}",
            "fallback": (
                f"Open FL Studio browser (F8), navigate to {preset.parent}, "
                f"and drag '{preset.name}' to the channel rack."
            ),
            "preset_path": preset_path,
        }
