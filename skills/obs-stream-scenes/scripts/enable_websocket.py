#!/usr/bin/env python3
"""Turn on OBS's WebSocket server (port 4455, password protected) by writing its config file.

    python enable_websocket.py [--port 4455] [--show-password]

Run it with OBS CLOSED, then open OBS. Saves the user a trip through
Tools > WebSocket Server Settings. An existing password is kept; otherwise a random one is created.
The password stays in OBS's own config, where configure_obs.py reads it, so it is never printed unless
--show-password is passed (needed only to pair a phone remote such as OBS Blade).

Works with OBS 28 or newer (obs-websocket 5 is built in).
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from obs_paths import obs_config_dir, obs_is_running, read_websocket_config, websocket_config_file  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=4455)
    p.add_argument("--show-password", action="store_true")
    args = p.parse_args()

    if not obs_config_dir().exists():
        print(f"OBS config not found at {obs_config_dir()}. Install OBS and open it once, then close it and run this again.",
              file=sys.stderr)
        return 1
    if obs_is_running():
        print("OBS is open. Close it first: OBS rewrites this file on exit.", file=sys.stderr)
        return 1

    cfg = read_websocket_config()
    password = cfg.get("server_password") or secrets.token_urlsafe(12)
    cfg.update({
        "alerts_enabled": cfg.get("alerts_enabled", False),
        "auth_required": True,
        "first_load": False,
        "server_enabled": True,
        "server_password": password,
        "server_port": cfg.get("server_port") or args.port,
    })
    path: Path = websocket_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    print(f"WebSocket enabled on port {cfg['server_port']} with a password (stored in {path}).")
    if args.show_password:
        print("Password:", password)
    print("Now open OBS. On Windows, allow OBS through the firewall if asked (only needed for phone remotes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
