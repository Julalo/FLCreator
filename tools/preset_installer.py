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
        await ctx.info(f"Downloading preset from {preset_url} ...")

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
                await ctx.info("Extracting zip archive...")
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
                await ctx.info(f"Installed: {dest}")

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


def _get_fl_channel_rack_position(fl_win, channel_index: Optional[int]) -> tuple[int, int]:
    """
    Estimate the screen coordinates of a channel rack slot.
    FL Studio's channel rack starts roughly 150px from the top of the window
    and 60px from the left. Each channel row is ~22px tall.
    """
    base_x = fl_win.left + 120
    base_y = fl_win.top + 150
    if channel_index is not None:
        base_y += channel_index * 22
    return base_x, base_y


async def load_preset_in_fl(
    preset_path: str,
    channel_index: Optional[int] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Load a .fst preset into FL Studio by opening Windows Explorer at the preset
    folder, then performing a real OS-level drag from Explorer to the FL Studio
    channel rack using pyautogui.

    Requires FL Studio to be running in windowed (non-maximized) mode.
    """
    import subprocess

    preset = Path(preset_path)
    if not preset.exists():
        return {"error": f"Preset file not found: {preset_path}"}
    if preset.suffix.lower() != ".fst":
        return {
            "error": f"Only .fst files can be dragged into FL Studio. Got: {preset.suffix}",
            "preset_path": preset_path,
        }

    try:
        import pygetwindow as gw  # type: ignore
    except ImportError:
        return {"error": "pygetwindow not installed. Run: pip install pygetwindow"}

    try:
        import pyautogui  # type: ignore
    except ImportError:
        return {"error": "pyautogui not installed. Run: pip install pyautogui"}

    # ── 1. Find FL Studio ────────────────────────────────────────────────────
    fl_windows = [w for w in gw.getAllWindows() if "FL Studio" in w.title]
    if not fl_windows:
        return {"error": "FL Studio is not open. Launch FL Studio first."}

    fl_win = fl_windows[0]

    if ctx:
        await ctx.info(f"FL Studio window: '{fl_win.title}' at ({fl_win.left},{fl_win.top})")

    # Refuse to proceed if FL is maximized — drag target coords will be wrong
    import ctypes
    try:
        hwnd = fl_win._hWnd  # pygetwindow exposes the HWND on Windows
        placement = ctypes.windll.user32.IsZoomed(hwnd)
        if placement:
            return {
                "error": (
                    "FL Studio is maximized. Restore it to a window (press Win+Down or drag "
                    "the title bar) so the channel rack position can be calculated correctly."
                )
            }
    except Exception:
        pass  # If we can't check, proceed anyway

    # ── 2. Open Windows Explorer with the preset file selected ───────────────
    if ctx:
        await ctx.info(f"Opening Explorer at: {preset.parent}")

    subprocess.Popen(["explorer", f"/select,{preset}"])
    time.sleep(2.0)  # Give Explorer time to open and render

    # Find the Explorer window — its title is the parent folder name
    explorer_title = preset.parent.name
    explorer_windows = [
        w for w in gw.getAllWindows()
        if explorer_title.lower() in w.title.lower() or "File Explorer" in w.title
    ]

    if not explorer_windows:
        # Explorer opened but we couldn't find the window — fall back gracefully
        if ctx:
            await ctx.error("Explorer window not found after opening.")
        return {
            "success": False,
            "error": (
                "Could not locate the Explorer window automatically. "
                f"Open this folder manually and drag the file to FL Studio:\n{preset}"
            ),
        }

    exp_win = explorer_windows[0]

    try:
        exp_win.activate()
        time.sleep(0.4)
    except Exception:
        pass

    # ── 3. Calculate positions ───────────────────────────────────────────────
    # The selected file sits roughly in the center of the Explorer content area.
    # Explorer's content pane starts ~40px below the toolbar and ~200px from the left
    # (accounting for the navigation pane).
    file_x = exp_win.left + exp_win.width // 2
    file_y = exp_win.top + int(exp_win.height * 0.45)

    rack_x, rack_y = _get_fl_channel_rack_position(fl_win, channel_index)

    if ctx:
        await ctx.info(
            f"Drag: Explorer ({file_x},{file_y}) → FL channel rack ({rack_x},{rack_y})"
        )

    # ── 4. Perform the drag ──────────────────────────────────────────────────
    try:
        pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
        pyautogui.PAUSE = 0.05

        # Click the file to make sure it's selected
        pyautogui.moveTo(file_x, file_y, duration=0.3)
        time.sleep(0.15)
        pyautogui.click()
        time.sleep(0.2)

        # Drag to FL Studio channel rack
        pyautogui.mouseDown(button="left")
        time.sleep(0.15)

        # Move in small steps for reliability (some apps need slow drags)
        pyautogui.moveTo(file_x, file_y - 10, duration=0.1)   # lift slightly
        pyautogui.moveTo(rack_x, rack_y, duration=0.9)         # drag across
        time.sleep(0.2)

        pyautogui.mouseUp(button="left")
        time.sleep(0.3)

        if ctx:
            await ctx.info("Drag completed.")

        return {
            "success": True,
            "preset_path": preset_path,
            "fl_window": fl_win.title,
            "channel_index": channel_index,
            "message": (
                f"Dragged '{preset.name}' from Explorer to the FL Studio channel rack. "
                "If the preset did not load, make sure FL Studio is in windowed mode "
                "and not maximized, then try again."
            ),
            "tip": (
                "If the drag landed in the wrong channel, call load_preset_in_fl again "
                "with channel_index set to the exact channel number (0 = first channel)."
            ),
        }

    except pyautogui.FailSafeException:
        return {
            "error": "Drag aborted — mouse moved to top-left corner (pyautogui failsafe).",
            "preset_path": preset_path,
        }
    except Exception as exc:
        if ctx:
            await ctx.error(f"Drag failed: {exc}")
        return {
            "error": f"Drag failed: {exc}",
            "fallback": (
                f"Explorer is open at the preset folder. "
                f"Drag '{preset.name}' to the FL Studio channel rack manually."
            ),
            "preset_path": preset_path,
        }
