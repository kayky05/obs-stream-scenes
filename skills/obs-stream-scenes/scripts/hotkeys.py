#!/usr/bin/env python3
"""Write the kit's hotkeys into OBS (scene switching, record, stream).

    python hotkeys.py <kit_dir> [--force]

Run it with OBS CLOSED: OBS rewrites its config files on exit and would erase the change.
Scene hotkeys go into the scene collection file; record and stream hotkeys into the profile.

Hotkey syntax in studio.json: "Ctrl+Alt+1", "Ctrl+Shift+F5", "Alt+R", "Cmd+Option+2" (macOS).
OBS hotkeys are global: they work while the browser or the game has focus.
"""

from __future__ import annotations

import argparse
import configparser
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from obs_paths import find_collection_file, find_profile_ini, load_lock, obs_is_running  # noqa: E402

MODS = {"ctrl": "control", "control": "control", "alt": "alt", "option": "alt", "shift": "shift",
        "cmd": "command", "command": "command", "win": "command", "super": "command", "meta": "command"}


def parse_combo(text: str) -> dict:
    parts = [p.strip() for p in text.replace(" ", "").split("+") if p.strip()]
    if not parts:
        raise ValueError(f"empty hotkey {text!r}")
    combo: dict = {}
    for mod in parts[:-1]:
        if mod.lower() not in MODS:
            raise ValueError(f"unknown modifier {mod!r} in {text!r}")
        combo[MODS[mod.lower()]] = True
    key = parts[-1]
    up = key.upper()
    if len(up) == 1 and (up.isalnum()):
        combo["key"] = f"OBS_KEY_{up}"
    elif up.startswith("F") and up[1:].isdigit():
        combo["key"] = f"OBS_KEY_{up}"
    elif up.startswith("NUM") and up[3:].isdigit():
        combo["key"] = f"OBS_KEY_NUM{up[3:]}"
    else:
        named = {"SPACE": "SPACE", "HOME": "HOME", "END": "END", "PAGEUP": "PAGEUP", "PAGEDOWN": "PAGEDOWN",
                 "INSERT": "INSERT", "DELETE": "DELETE", "PAUSE": "PAUSE"}
        if up not in named:
            raise ValueError(f"unsupported key {key!r} in {text!r}")
        combo["key"] = f"OBS_KEY_{named[up]}"
    return combo


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kit")
    p.add_argument("--force", action="store_true", help="write even if OBS seems to be running")
    args = p.parse_args()
    lock = load_lock(args.kit)

    if obs_is_running() and not args.force:
        print("OBS is open. Close it first (it would overwrite the hotkeys when it exits).", file=sys.stderr)
        return 1

    collection = find_collection_file(lock["obs"]["collection"])
    profile = find_profile_ini(lock["obs"]["profile"])
    if not collection or not profile:
        print("Scene collection or profile not found. Run configure_obs.py first (with OBS open).", file=sys.stderr)
        return 1

    seen: dict[str, str] = {}

    def register(label: str, text: str | None) -> list[dict]:
        if not text:
            return []
        combo = parse_combo(text)
        sig = json.dumps(combo, sort_keys=True)
        if sig in seen:
            raise SystemExit(f"Hotkey {text} is used twice: {seen[sig]} and {label}")
        seen[sig] = label
        return [combo]

    data = json.loads(collection.read_text(encoding="utf-8"))
    scene_keys = {sc["name"]: sc.get("hotkey") for sc in lock["scenes"]}
    for source in data.get("sources", []):
        if source.get("id") == "scene" and source.get("name") in scene_keys:
            bindings = register(source["name"], scene_keys[source["name"]])
            source.setdefault("hotkeys", {})["OBSBasic.SelectScene"] = bindings
    collection.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")

    ini = configparser.RawConfigParser(strict=False)
    ini.optionxform = str  # OBS keys are case sensitive
    ini.read(profile, encoding="utf-8-sig")
    if not ini.has_section("Hotkeys"):
        ini.add_section("Hotkeys")
    hk = lock["hotkeys"]
    for action, text in (("Recording", hk.get("record")), ("Streaming", hk.get("stream"))):
        bindings = json.dumps({"bindings": register(action, text)})
        # the same combo on Start and Stop makes one key toggle
        ini.set("Hotkeys", f"OBSBasic.Start{action}", bindings)
        ini.set("Hotkeys", f"OBSBasic.Stop{action}", bindings)
    with profile.open("w", encoding="utf-8") as fh:
        ini.write(fh, space_around_delimiters=False)

    for sig, label in seen.items():
        print(f"{label:<28} {'+'.join(k for k, v in json.loads(sig).items() if v is True)}+{json.loads(sig)['key'].replace('OBS_KEY_', '')}")
    print("Hotkeys written. Open OBS and test them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
