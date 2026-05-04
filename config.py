"""
config.py — Loads and validates fl_studio_mcp configuration from config.json.
Falls back to config.example.json if config.json is missing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent

_CONFIG: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    config_path = ROOT / "config.json"
    if not config_path.exists():
        config_path = ROOT / "config.example.json"
    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    # Resolve {USER} placeholder
    username = os.environ.get("USERNAME") or os.environ.get("USER") or "User"
    raw_str = json.dumps(raw).replace("{USER}", username)
    return json.loads(raw_str)


def get_config() -> dict[str, Any]:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load()
    return _CONFIG


def fl_user_data() -> Path:
    cfg = get_config()
    return Path(cfg["fl_studio"]["user_data_folder"])


def fl_install() -> Path:
    cfg = get_config()
    return Path(cfg["fl_studio"]["install_folder"])


def vst_folders() -> list[Path]:
    cfg = get_config()
    return [Path(p) for p in cfg["fl_studio"]["vst_folders"]]


def sample_scan_folders() -> list[Path]:
    cfg = get_config()
    return [Path(p) for p in cfg["samples"]["scan_folders"]]


def midi_port_name() -> str:
    return get_config()["midi"]["port_name"]


def default_velocity() -> int:
    return get_config()["midi"]["default_velocity"]


def default_bpm() -> int:
    return get_config()["midi"]["default_bpm"]


def cache_folder() -> Path:
    cfg = get_config()
    p = Path(cfg.get("cache_folder", "./cache"))
    if not p.is_absolute():
        p = ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def anthropic_api_key() -> str:
    return get_config().get("anthropic_api_key", "")


def auto_research_plugins() -> bool:
    return get_config().get("auto_research_plugins", True)


def plugins_db_generators() -> Path:
    return fl_user_data() / "Presets" / "Plugin database" / "Installed" / "Generators"


def plugins_db_effects() -> Path:
    return fl_user_data() / "Presets" / "Plugin database" / "Installed" / "Effects"


def fl_presets_generators() -> Path:
    return fl_user_data() / "Presets" / "Plugin database" / "Installed" / "Generators"


def fl_presets_effects() -> Path:
    return fl_user_data() / "Presets" / "Plugin database" / "Installed" / "Effects"
