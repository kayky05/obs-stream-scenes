"""Where OBS keeps its config on each OS, and helpers shared by the other scripts."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def obs_config_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path(os.environ["APPDATA"]) / "obs-studio"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "obs-studio"
    flatpak = Path.home() / ".var" / "app" / "com.obsproject.Studio" / "config" / "obs-studio"
    if flatpak.exists():
        return flatpak
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "obs-studio"


def websocket_config_file() -> Path:
    return obs_config_dir() / "plugin_config" / "obs-websocket" / "config.json"


def read_websocket_config() -> dict:
    path = websocket_config_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def obs_is_running() -> bool:
    system = platform.system()
    try:
        if system == "Windows":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"], capture_output=True, text=True, timeout=15).stdout
            return "obs64.exe" in out.lower()
        out = subprocess.run(["pgrep", "-x", "obs"], capture_output=True, text=True, timeout=15)
        return out.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def load_lock(kit: str) -> dict:
    path = Path(kit).expanduser().resolve() / "studio.lock.json"
    if not path.exists():
        sys.exit(f"{path} not found. Run build_kit.py {kit} first.")
    return json.loads(path.read_text(encoding="utf-8"))


def find_collection_file(name: str) -> Path | None:
    """OBS names the file after the collection but sanitizes it, so match on the 'name' field inside."""
    for path in sorted((obs_config_dir() / "basic" / "scenes").glob("*.json")):
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("name") == name:
                return path
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return None


def find_profile_ini(name: str) -> Path | None:
    for ini in sorted((obs_config_dir() / "basic" / "profiles").glob("*/basic.ini")):
        for line in ini.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            if line.strip() == f"Name={name}":
                return ini
    return None
