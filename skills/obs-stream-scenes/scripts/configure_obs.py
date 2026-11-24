#!/usr/bin/env python3
"""Build the OBS profile, scene collection, scenes and sources described in <kit>/studio.lock.json.

    pip install obsws-python
    python configure_obs.py <kit_dir> [--password PW] [--prune] [--dry-run]

OBS must be open with the WebSocket server on (enable_websocket.py does that). The password is read
from OBS's own websocket config when --password is omitted, so it never has to be typed or printed.

Idempotent: run it again after every build_kit.py. It updates what exists instead of duplicating,
removes scene items that are no longer in the layout, and keeps the user's other scenes unless
--prune is given (then every scene not in the kit is deleted from this collection).

Hotkeys are not reachable over the websocket: run hotkeys.py afterwards, with OBS closed.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from obs_paths import load_lock, read_websocket_config  # noqa: E402

ALIGN_TOP_LEFT = 5
DEFAULT_SCENE_NAMES = {"Scene", "Cena", "Escena", "Szene", "Scène"}

# input kinds per OS, first available wins; second item is the property that lists devices
KINDS = {
    "camera": [("dshow_input", "video_device_id"), ("macos-avcapture", "device"), ("av_capture_input", "device"), ("v4l2_input", "device_id")],
    "capture_card": [("dshow_input", "video_device_id"), ("macos-avcapture", "device"), ("av_capture_input", "device"), ("v4l2_input", "device_id")],
    "mic": [("wasapi_input_capture", "device_id"), ("coreaudio_input_capture", "device_id"), ("pulse_input_capture", "device_id")],
    "desktop": [("wasapi_output_capture", "device_id"), ("coreaudio_output_capture", "device_id"), ("pulse_output_capture", "device_id")],
    "screen": [("monitor_capture", "monitor_id"), ("screen_capture", "display_uuid"), ("display_capture", "display"), ("xshm_input", "screen"),
               ("pipewire-screen-capture-source", None)],
    "game": [("game_capture", None)],
    "window": [("window_capture", "window"), ("screen_capture", None), ("xcomposite_input", "capture_window"), ("pipewire-window-capture-source", None)],
    "browser": [("browser_source", None)],
}
TRANSPARENT_CSS = "body { background-color: rgba(0, 0, 0, 0); margin: 0; overflow: hidden; }"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kit")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int)
    p.add_argument("--password", help="websocket password (default: read from OBS's websocket config)")
    p.add_argument("--prune", action="store_true", help="delete every scene of this collection that is not in the kit")
    p.add_argument("--dry-run", action="store_true", help="print the requests instead of sending them")
    args = p.parse_args()
    lock = load_lock(args.kit)

    if args.dry_run:
        client = DryRunClient()
    else:
        try:
            import obsws_python as obs
        except ImportError:
            sys.exit("obsws-python is missing: python -m pip install obsws-python")
        ws = read_websocket_config()
        password = args.password or ws.get("server_password") or ""
        port = args.port or ws.get("server_port") or lock["obs"].get("websocket_port", 4455)
        try:
            client = obs.ReqClient(host=args.host, port=port, password=password, timeout=15)
        except Exception as exc:  # noqa: BLE001 - obsws raises several connection error types
            sys.exit(f"Could not connect to OBS on {args.host}:{port} ({exc}). Is OBS open? "
                     "Run enable_websocket.py with OBS closed, then open OBS and try again.")
    print("Connected to OBS", client.get_version().obs_version)
    s = Setup(client, lock)
    s.run(prune=args.prune)
    return 0


class Setup:
    def __init__(self, client, lock: dict) -> None:
        self.c = client
        self.lock = lock
        self.canvas = (lock["canvas"]["w"], lock["canvas"]["h"])
        self.available = set(client.get_input_kind_list(False).input_kinds)
        self.source_size: dict[str, tuple[int, int]] = {}

    def run(self, prune: bool) -> None:
        obs_cfg = self.lock["obs"]
        self.ensure_profile(obs_cfg["profile"])
        self.ensure_collection(obs_cfg["collection"])
        self.configure_output(obs_cfg)

        scene_names = [sc["name"] for sc in self.lock["scenes"]]
        existing = {s["sceneName"] for s in self.c.get_scene_list().scenes}
        for name in scene_names:
            if name not in existing:
                self.c.create_scene(name)
        for name in existing - set(scene_names):
            if prune or name in DEFAULT_SCENE_NAMES:
                self.c.remove_scene(name)

        mic = self.configure_mic()
        desktop = self.configure_desktop()
        inputs = {sid: self.ensure_source(sid, spec) for sid, spec in self.lock["sources"].items()}
        for sc in self.lock["scenes"]:
            self.build_scene(sc, inputs, mic, desktop)
        self.c.set_current_program_scene(scene_names[0])
        print("Done. Scenes:", ", ".join(scene_names))
        print("Next: close OBS and run hotkeys.py, then reopen OBS.")

    # ------------------------------------------------------------ profile, collection, output

    def ensure_profile(self, name: str) -> None:
        profiles = self.c.get_profile_list()
        if profiles.current_profile_name == name:
            return
        if name in profiles.profiles:
            self.c.set_current_profile(name)
        else:
            self.c.create_profile(name)
        time.sleep(1)

    def ensure_collection(self, name: str) -> None:
        cols = self.c.get_scene_collection_list()
        if cols.current_scene_collection_name == name:
            return
        if name in cols.scene_collections:
            self.c.set_current_scene_collection(name)
        else:
            self.c.create_scene_collection(name)
        time.sleep(2)

    def configure_output(self, o: dict) -> None:
        w, h = self.canvas
        self.c.set_video_settings(int(o["fps"]), 1, w, h, w, h)
        params = [
            ("Output", "Mode", "Simple"),
            ("SimpleOutput", "RecFormat2", o.get("format", "hybrid_mp4")),
            ("SimpleOutput", "RecQuality", o.get("quality", "HQ")),
            ("SimpleOutput", "RecEncoder", o.get("encoder", "nvenc")),
            ("SimpleOutput", "StreamEncoder", o.get("encoder", "nvenc")),
            ("SimpleOutput", "RecRB", "false"),
            ("Audio", "SampleRate", "48000"),
            ("Audio", "ChannelSetup", "Stereo"),
        ]
        if o.get("video_bitrate"):
            params.append(("SimpleOutput", "VBitrate", str(o["video_bitrate"])))
        if o.get("audio_bitrate"):
            params.append(("SimpleOutput", "ABitrate", str(o["audio_bitrate"])))
        for category, key, value in params:
            self.c.set_profile_parameter(category, key, value)
        folder = Path(o["recordings"])
        folder.mkdir(parents=True, exist_ok=True)
        self.c.set_profile_parameter("SimpleOutput", "FilePath", str(folder.resolve()))
        print(f"Output: {w}x{h} @ {o['fps']} fps, {o.get('encoder')}, recordings in {folder}")

    # ------------------------------------------------------------ audio

    def kind(self, role: str) -> tuple[str, str | None]:
        for kind, prop in KINDS[role]:
            if kind in self.available:
                return kind, prop
        raise RuntimeError(f"No OBS input kind for {role} on this system (tried {[k for k, _ in KINDS[role]]})")

    def configure_mic(self) -> str:
        name = self.lock["mic_name"]
        special = self.c.get_special_inputs()
        existing = self.input_names()
        if special.mic1 and special.mic1 != name and name not in existing:
            self.c.set_input_name(special.mic1, name)
        elif name not in existing:
            kind, _ = self.kind("mic")
            first = self.lock["scenes"][0]["name"]
            self.c.create_input(first, name, kind, {"device_id": "default"}, True)
        _, prop = self.kind("mic")
        device = self.pick(name, prop, self.lock["devices"].get("mic") or [])
        if device:
            self.c.set_input_settings(name, {prop: device["itemValue"]}, True)
            print("Microphone:", device["itemName"])
        else:
            print("Microphone: no device matched", self.lock["devices"].get("mic"), "- using the system default")
        audio = self.lock["audio"]
        have = {f["filterName"] for f in self.c.get_source_filter_list(name).filters}
        chain = []
        if audio.get("noise_suppression", True):
            chain.append(("Noise suppression", "noise_suppress_filter_v2", {"method": "rnnoise"}))
        if audio.get("compressor", True):
            chain.append(("Compressor", "compressor_filter", {"ratio": 4.0, "threshold": -18.0, "attack_time": 6, "release_time": 60, "output_gain": 0.0}))
        if audio.get("limiter", True):
            chain.append(("Limiter", "limiter_filter", {"threshold": -3.0, "release_time": 60}))
        for fname, fkind, settings in chain:
            if fname not in have:
                self.c.create_source_filter(name, fname, fkind, settings)
        return name

    def configure_desktop(self) -> str | None:
        special = self.c.get_special_inputs()
        globals_ = [d for d in (special.desktop1, special.desktop2) if d]
        if not self.lock["audio"].get("desktop_audio"):
            for d in globals_:
                self.c.remove_input(d)
            print("Desktop audio: removed (notifications and system sounds stay out of the video)")
            return None
        if globals_:
            print("Desktop audio: kept (global source", globals_[0] + ")")
            return None  # global sources play in every scene already
        name = self.lock["desktop_name"]
        if name not in self.input_names():
            kind, _ = self.kind("desktop")
            self.c.create_input(self.lock["scenes"][0]["name"], name, kind, {"device_id": "default"}, True)
        print("Desktop audio:", name)
        return name

    # ------------------------------------------------------------ sources

    def ensure_source(self, sid: str, spec: dict) -> str:
        name = spec["name"]
        stype = spec["type"]
        first_scene = self.lock["scenes"][0]["name"]
        if stype in ("camera", "capture_card"):
            kind, prop = self.kind(stype)
            res = self.lock["devices"].get("camera_resolution", "1920x1080")
            settings = {"res_type": 1, "resolution": res, "frame_interval": -1,  # -1 = match the output fps
                        "deactivate_when_not_showing": False, "active": True} if kind == "dshow_input" else {}
            self.upsert_input(first_scene, name, kind, settings)
            device = self.pick(name, prop, spec.get("hint") or [])
            if device:
                self.c.set_input_settings(name, {prop: device["itemValue"]}, True)
                print(f"{name}: {device['itemName']}")
            else:
                print(f"{name}: no device matched {spec.get('hint')} - pick it in the source properties")
        elif stype == "screen":
            kind, prop = self.kind("screen")
            self.upsert_input(first_scene, name, kind, {"capture_cursor": True, "show_cursor": True})
            if prop:
                items = [m for m in self.list_items(name, prop) if m.get("itemValue") and m.get("itemEnabled", True)]
                if items:
                    chosen = items[min(int(spec.get("monitor", 0)), len(items) - 1)]
                    self.c.set_input_settings(name, {prop: chosen["itemValue"]}, True)
                    print(f"{name}: {chosen['itemName']}")
        elif stype == "game":
            if "game_capture" in self.available:
                self.upsert_input(first_scene, name, "game_capture", {"capture_mode": "any_fullscreen", "capture_cursor": False})
                print(f"{name}: game capture, any full-screen game")
            else:
                kind, _ = self.kind("screen")
                self.upsert_input(first_scene, name, kind, {})
                print(f"{name}: no game capture on this OS, using screen capture")
        elif stype == "window":
            kind, _ = self.kind("window")
            self.upsert_input(first_scene, name, kind, {"capture_cursor": False})
            print(f"{name}: window capture - open the browser or player and pick the window in the source properties")
        elif stype == "browser":
            w, h = self.first_rect_size(sid)
            settings = {"is_local_file": False, "url": spec["url"], "width": w, "height": h, "css": TRANSPARENT_CSS,
                        "shutdown": False, "restart_when_active": False, "reroute_audio": False}
            self.upsert_input(first_scene, name, "browser_source", settings)
            print(f"{name}: {spec['url']}")
        return name

    def layer_input(self, sc: dict, layer: str) -> str:
        name = f"{sc['name']} · {self.lock['layer_names'][layer]}"
        w, h = self.canvas
        settings = {"is_local_file": True, "local_file": sc["files"][layer], "width": w, "height": h,
                    "fps_custom": True, "fps": 30, "css": TRANSPARENT_CSS if layer == "fg" else "",
                    "shutdown": False, "restart_when_active": bool(sc.get("restart")), "reroute_audio": False}
        self.upsert_input(sc["name"], name, "browser_source", settings)
        return name

    # ------------------------------------------------------------ scenes

    def build_scene(self, sc: dict, inputs: dict, mic: str, desktop: str | None) -> None:
        scene = sc["name"]
        order: list[tuple[str, dict | None]] = []  # (source name, slot) bottom to top
        if "bg" in sc.get("files", {}):
            order.append((self.layer_input(sc, "bg"), None))
        order += [(inputs[s["source"]], s) for s in sc["slots"] if s["z"] == "under"]
        if "fg" in sc.get("files", {}):
            order.append((self.layer_input(sc, "fg"), None))
        order += [(inputs[s["source"]], s) for s in sc["slots"] if s["z"] == "over"]
        audio = [mic] if sc.get("mic") else []
        if desktop:
            audio.append(desktop)

        wanted = {n for n, _ in order} | set(audio)
        items = {it["sourceName"]: it["sceneItemId"] for it in self.c.get_scene_item_list(scene).scene_items}
        for src, item_id in items.items():
            if src not in wanted:
                self.c.remove_scene_item(scene, item_id)
        # the same source can appear twice in one scene only in custom layouts; keep one item per source
        for index, (src, slot) in enumerate(order):
            item_id = items.get(src)
            if item_id is None:
                item_id = self.c.create_scene_item(scene, src, True).scene_item_id
                items[src] = item_id
            self.c.set_scene_item_index(scene, item_id, index)
            if slot is None:
                self.place(scene, item_id, {"positionX": 0, "positionY": 0, "scaleX": 1.0, "scaleY": 1.0})
            else:
                self.place_slot(scene, item_id, src, slot)
        for src in audio:
            if src not in items:
                self.c.create_scene_item(scene, src, True)
        print(f"Scene {scene}: {', '.join(n for n, _ in order) or 'empty'}")

    def place_slot(self, scene: str, item_id, src: str, slot: dict) -> None:
        x, y, w, h = slot["rect"]
        if slot["fit"] == "cover":
            sw, sh = self.size_of(scene, item_id, src)
            self.place(scene, item_id, cover(sw, sh, w, h, x, y))
        else:
            self.place(scene, item_id, {"positionX": x, "positionY": y, "boundsType": "OBS_BOUNDS_SCALE_INNER",
                                        "boundsWidth": w, "boundsHeight": h, "boundsAlignment": 0})

    def size_of(self, scene: str, item_id, src: str) -> tuple[int, int]:
        """Cameras report their real size a moment after opening; wait briefly for it."""
        if src in self.source_size:
            return self.source_size[src]
        fallback = tuple(int(v) for v in self.lock["devices"].get("camera_resolution", "1920x1080").split("x"))
        for _ in range(8):
            t = self.c.get_scene_item_transform(scene, item_id).scene_item_transform
            sw, sh = int(t.get("sourceWidth") or 0), int(t.get("sourceHeight") or 0)
            if sw and sh:
                self.source_size[src] = (sw, sh)
                return sw, sh
            time.sleep(0.5)
        print(f"  {src}: size not reported yet, assuming {fallback[0]}x{fallback[1]} (re-run this script once the camera shows image)")
        return fallback  # type: ignore[return-value]

    def place(self, scene: str, item_id, transform: dict) -> None:
        base = {"alignment": ALIGN_TOP_LEFT, "rotation": 0.0, "boundsType": "OBS_BOUNDS_NONE", "boundsWidth": 1.0, "boundsHeight": 1.0,
                "cropLeft": 0, "cropRight": 0, "cropTop": 0, "cropBottom": 0}
        base.update(transform)
        self.c.set_scene_item_transform(scene, item_id, base)

    # ------------------------------------------------------------ helpers

    def input_names(self) -> set[str]:
        return {i["inputName"] for i in self.c.get_input_list().inputs}

    def upsert_input(self, scene: str, name: str, kind: str, settings: dict) -> None:
        if name in self.input_names():
            self.c.set_input_settings(name, settings, True)
        else:
            self.c.create_input(scene, name, kind, settings, True)

    def list_items(self, input_name: str, prop: str) -> list[dict]:
        try:
            return list(self.c.get_input_properties_list_property_items(input_name, prop).property_items)
        except Exception:  # noqa: BLE001 - property missing on this OS
            return []

    def pick(self, input_name: str, prop: str | None, hints: list[str]) -> dict | None:
        if not prop:
            return None
        items = self.list_items(input_name, prop)
        for h in (x.strip().lower() for x in hints if x.strip()):
            for it in items:
                if h in str(it.get("itemName", "")).lower() and it.get("itemEnabled", True):
                    return it
        return None

    def first_rect_size(self, sid: str) -> tuple[int, int]:
        for sc in self.lock["scenes"]:
            for s in sc["slots"]:
                if s["source"] == sid:
                    return s["rect"][2], s["rect"][3]
        return self.canvas


def cover(src_w: int, src_h: int, w: int, h: int, x: int, y: int) -> dict:
    """Crop the source to the target aspect (no distortion) and scale it to fill."""
    target = w / h
    if src_w / src_h > target:
        keep_w = round(src_h * target)
        side = (src_w - keep_w) // 2
        crop = {"cropLeft": side, "cropRight": src_w - keep_w - side, "cropTop": 0, "cropBottom": 0}
        scale = w / keep_w
    else:
        keep_h = round(src_w / target)
        top = (src_h - keep_h) // 2
        crop = {"cropLeft": 0, "cropRight": 0, "cropTop": top, "cropBottom": src_h - keep_h - top}
        scale = h / keep_h
    return {"positionX": x, "positionY": y, "scaleX": scale, "scaleY": scale, **crop}


# ---------------------------------------------------------------- dry run


class _Nothing:
    """Stands in for any websocket response during --dry-run: empty, falsy, chainable."""
    def __getattr__(self, name): return _Nothing()
    def __call__(self, *a, **k): return _Nothing()
    def __iter__(self): return iter(())
    def __bool__(self): return False
    def __getitem__(self, key): return _Nothing()
    def get(self, key, default=None): return default
    def __repr__(self): return "<id>"


class DryRunClient:
    QUIET = {"get_scene_list", "get_input_list", "get_scene_item_list", "get_special_inputs", "get_profile_list",
             "get_scene_collection_list", "get_source_filter_list", "get_input_properties_list_property_items",
             "get_scene_item_transform"}

    def get_version(self):
        return SimpleNamespace(obs_version="dry-run")

    def get_input_kind_list(self, _unversioned):
        return SimpleNamespace(input_kinds=[k for kinds in KINDS.values() for k, _ in kinds])

    def __getattr__(self, name):
        def call(*args, **kwargs):
            if name not in self.QUIET:
                shown = ", ".join(repr(a)[:90] for a in args)
                print(f"  -> {name}({shown})")
            return _Nothing()
        return call


if __name__ == "__main__":
    sys.exit(main())
