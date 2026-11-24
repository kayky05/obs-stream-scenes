"""Scene presets: each one turns a short scene entry from studio.json into exact geometry.

A preset returns:
  slots : OBS sources placed in the scene, bottom to top, each {"source", "rect": [x, y, w, h], "fit", "z"}
          fit "cover" crops to fill the rect (cameras), "contain" fits inside it (screens, games, videos)
          z   "under" sits below the foreground layer, "over" sits above it (cameras over their frame)
  bg    : elements drawn by the opaque background browser source (None = no background layer)
  fg    : elements drawn by the transparent foreground browser source (None = no foreground layer)
  mic   : whether the microphone belongs in the scene
  restart: whether the browser layers restart when the scene goes live (countdowns)

All geometry targets the canvas in ctx["canvas"]. The numbers come from layouts that shipped on real
channels: keep a 40 px safe margin, 16:9 content boxes, cameras 4:3 or 16:9, and a 10 px frame
around every captured box (the frame is drawn 10 px outside the rect).
"""

from __future__ import annotations

W16 = 16 / 9


def r(x: float, y: float, w: float, h: float) -> list[int]:
    return [round(x), round(y), round(w), round(h)]


def slot(source: str, rect: list[int], fit: str = "contain", z: str = "under") -> dict:
    return {"source": source, "rect": rect, "fit": fit, "z": z}


def frame(rect: list[int]) -> dict:
    return {"type": "frame", "rect": rect}


def corner_rect(corner: str, w: int, h: int, cw: int, ch: int, inset: int = 40) -> list[int]:
    x = inset if "left" in corner else cw - inset - w
    y = inset if "top" in corner else ch - inset - h
    return r(x, y, w, h)


def opposite_anchor(corner: str) -> str:
    vertical = "bottom" if "bottom" in corner else "top"
    horizontal = "left" if "right" in corner else "right"
    return f"{vertical}-{horizontal}"


# ---------------------------------------------------------------- recorded lessons


def tutorial(scene: dict, ctx: dict) -> dict:
    """Screen in a big frame, camera in a small one, brand and lesson title in the side column."""
    cw, ch = ctx["canvas"]
    side = scene.get("camera_side", "left")
    screen = r(560, 112, 1280, 720)
    cam = r(80, 688, 416, 312)
    if side == "right":
        screen = r(80, 112, 1280, 720)
        cam = r(cw - 80 - 416, 688, 416, 312)
    col_x, col_w = cam[0], cam[2]
    rail_x = col_x - 20 if side == "left" else col_x + col_w + 20
    content = scene.get("content", "screen")
    label_key, title_key = scene.get("label_key", "label"), scene.get("title_key", "title")
    bg = [
        {"type": "backdrop", "rail_x": rail_x, "glow": "right" if side == "left" else "left"},
        {"type": "rule", "x": col_x, "y": cam[1] - 48, "w": col_w},
        frame(screen), frame(cam),
        {"type": "brand", "x": col_x, "y": screen[1], "w": col_w, "size": "lg"},
        {"type": "text", "key": label_key, "style": "label", "x": col_x, "y": cam[1] - 212, "w": col_w},
        {"type": "text", "key": title_key, "style": "title", "x": col_x - 2, "y": cam[1] - 182, "w": col_w, "lines": 3},
        {"type": "foot", "x": screen[0], "y": screen[1] + screen[3] + 40, "w": screen[2]},
    ]
    return {"slots": [slot(content, screen), slot("camera", cam, "cover")], "bg": bg, "fg": None, "mic": True, "restart": False}


# ---------------------------------------------------------------- full-canvas content + picture in picture


def fullscreen_pip(scene: dict, ctx: dict) -> dict:
    """Content fills the canvas (screen, game, browser window), camera in a corner, optional pill.

    Used for: tutorial detail shots, PC gameplay, react with the video in full screen.
    """
    cw, ch = ctx["canvas"]
    content = scene.get("content", "screen")
    corner = scene.get("camera_corner", "bottom-right")
    shape = scene.get("camera_shape", "square")
    slots = [slot(content, r(0, 0, cw, ch))]
    fg: list[dict] = []
    if shape != "none":
        if shape == "square":
            size = scene.get("camera_size", 240)
            cam = corner_rect(corner, size, size, cw, ch)
        else:  # wide 16:9
            w = scene.get("camera_size", 432)
            cam = corner_rect(corner, w, round(w / W16), cw, ch)
        fg.append(frame(cam))
        slots.append(slot("camera", cam, "cover", "over"))
    pill_key = scene.get("pill_key", "title")
    if pill_key:
        fg.append({"type": "pill", "anchor": opposite_anchor(corner), "key": pill_key})
    if scene.get("badge"):
        fg.append({"type": "badge", "anchor": "top-left" if "right" in corner else "top-right"})
    if scene.get("chat") and "chat" in ctx["sources"]:
        chat_w, chat_h = 400, 620
        chat_x = cw - 40 - chat_w if "left" in corner else 40
        chat = r(chat_x, 120, chat_w, chat_h)
        fg.append({"type": "panel", "rect": chat})
        slots.append(slot("chat", chat, "contain", "over"))
    return {"slots": slots, "bg": None, "fg": fg or None, "mic": True, "restart": False}


def gameplay(scene: dict, ctx: dict) -> dict:
    defaults = {"content": "game", "camera_shape": "wide", "camera_corner": "bottom-left", "pill_key": None, "badge": ctx["live"]}
    return fullscreen_pip({**defaults, **scene}, ctx)


def react_pip(scene: dict, ctx: dict) -> dict:
    defaults = {"content": "window", "camera_shape": "wide", "camera_corner": "bottom-right", "camera_size": 480, "pill_key": "react", "badge": ctx["live"]}
    return fullscreen_pip({**defaults, **scene}, ctx)


# ---------------------------------------------------------------- framed content + side column (camera, chat)


def framed(scene: dict, ctx: dict) -> dict:
    """Content in a big 16:9 frame, a side column with the camera and the chat (or the brand).

    Used for: react, framed gameplay, console gameplay, webinars.
    """
    cw, ch = ctx["canvas"]
    content = scene.get("content", "window")
    side = scene.get("content_side", "left")  # where the big content box goes
    box = (1408, 792)
    col_w = cw - 40 - box[0] - 40 - 40  # 392 on 1920
    if side == "left":
        content_rect = r(40, 60, *box)
        col_x = 40 + box[0] + 40
    else:
        content_rect = r(cw - 40 - box[0], 60, *box)
        col_x = 40
    cam = r(col_x, 60, col_w, round(col_w * 3 / 4))
    bg = [
        {"type": "backdrop", "rail_x": None, "glow": "left" if side == "right" else "right"},
        frame(content_rect), frame(cam),
    ]
    slots = [slot(content, content_rect), slot("camera", cam, "cover")]
    below_cam_y = cam[1] + cam[3] + 40
    if scene.get("chat", True) and "chat" in ctx["sources"]:
        chat = r(col_x, below_cam_y, col_w, content_rect[1] + content_rect[3] - below_cam_y)
        bg.append({"type": "panel", "rect": chat})
        slots.append(slot("chat", chat, "contain"))
    else:
        bg.append({"type": "brand", "x": col_x, "y": below_cam_y + 10, "w": col_w, "size": "md"})
    bar_y = content_rect[1] + content_rect[3] + 34
    text_key = scene.get("text_key", "react" if content in ("window", "browser") else "title")
    bg.append({"type": "text", "key": text_key, "style": "caption", "x": content_rect[0], "y": bar_y, "w": content_rect[2] - 420, "lines": 1})
    bg.append({"type": "socials", "x": content_rect[0] + content_rect[2] - 400, "y": bar_y + 6, "w": 400, "align": "right"})
    if ctx["live"]:
        bg.append({"type": "badge", "x": col_x, "y": ch - 40 - 40})
    return {"slots": slots, "bg": bg, "fg": None, "mic": True, "restart": False}


def gameplay_framed(scene: dict, ctx: dict) -> dict:
    return framed({"content": "game", "text_key": "title", **scene}, ctx)


def react(scene: dict, ctx: dict) -> dict:
    return framed({"content": "window", "text_key": "react", **scene}, ctx)


# ---------------------------------------------------------------- cameras


def camera_full(scene: dict, ctx: dict) -> dict:
    cw, ch = ctx["canvas"]
    source = scene.get("camera", "camera")
    fg = None
    if scene.get("lower_third"):
        fg = [{"type": "pill", "anchor": "bottom-left", "key": scene.get("pill_key", "title")}]
        if ctx["live"]:
            fg.append({"type": "badge", "anchor": "top-left"})
    return {"slots": [slot(source, r(0, 0, cw, ch), "cover")], "bg": None, "fg": fg, "mic": True, "restart": False}


def just_chatting(scene: dict, ctx: dict) -> dict:
    """Camera large in a frame, chat in the side column."""
    if "chat" not in ctx["sources"]:
        return camera_full({"lower_third": True, **scene}, ctx)
    cw, ch = ctx["canvas"]
    cam = r(40, 60, 1408, 792)
    col_x = 40 + 1408 + 40
    col_w = cw - 40 - col_x
    chat = r(col_x, 60, col_w, 792)
    bar_y = cam[1] + cam[3] + 34
    bg = [
        {"type": "backdrop", "rail_x": None, "glow": "right"},
        frame(cam), {"type": "panel", "rect": chat},
        {"type": "text", "key": scene.get("text_key", "title"), "style": "caption", "x": cam[0], "y": bar_y, "w": cam[2] - 420, "lines": 1},
        {"type": "socials", "x": cam[0] + cam[2] - 400, "y": bar_y + 6, "w": 400, "align": "right"},
    ]
    if ctx["live"]:
        bg.append({"type": "badge", "x": col_x, "y": ch - 40 - 40})
    return {"slots": [slot("camera", cam, "cover"), slot("chat", chat)], "bg": bg, "fg": None, "mic": True, "restart": False}


def side_by_side(scene: dict, ctx: dict) -> dict:
    """Two equal 16:9 boxes: react (video + camera) or podcast (camera + camera2)."""
    cw, ch = ctx["canvas"]
    left, right = scene.get("left", "window"), scene.get("right", "camera")
    w = (cw - 40 - 40 - 80) // 2  # 880 on 1920
    h = round(w / W16)
    y = round((ch - h) / 2)
    a, b = r(40, y, w, h), r(40 + w + 80, y, w, h)
    bg = [
        {"type": "backdrop", "rail_x": None, "glow": "right"},
        frame(a), frame(b),
        {"type": "brand", "x": 40, "y": 60, "w": 700, "size": "sm"},
        {"type": "text", "key": scene.get("text_key", "title"), "style": "headline", "x": 40, "y": y - 110, "w": cw - 80, "lines": 1},
        {"type": "foot", "x": 40, "y": y + h + 50, "w": cw - 80},
    ]
    fits = {s: ("cover" if s.startswith("camera") else "contain") for s in (left, right)}
    return {"slots": [slot(left, a, fits[left]), slot(right, b, fits[right])], "bg": bg, "fg": None, "mic": True, "restart": False}


# ---------------------------------------------------------------- full-screen messages (live only)


def message(scene: dict, ctx: dict) -> dict:
    """Starting soon / be right back / ending: centred brand, headline, optional countdown, socials."""
    cw, ch = ctx["canvas"]
    kind = scene.get("kind", "starting")
    key = scene.get("text_key", kind)
    bg = [
        {"type": "backdrop", "rail_x": None, "glow": "center"},
        {"type": "brand", "x": 0, "y": round(ch * 0.22), "w": cw, "size": "md", "align": "center"},
        {"type": "text", "key": key, "style": "display", "x": 160, "y": round(ch * 0.46), "w": cw - 320, "align": "center", "lines": 2},
    ]
    minutes = scene.get("countdown_min", 5 if kind == "starting" else 0)
    if minutes:
        bg.append({"type": "countdown", "minutes": minutes, "x": 0, "y": round(ch * 0.66), "w": cw, "align": "center"})
    bg.append({"type": "socials", "x": 0, "y": ch - 120, "w": cw, "align": "center"})
    return {"slots": [], "bg": bg, "fg": None, "mic": bool(scene.get("mic", False)), "restart": bool(minutes)}


def starting(scene: dict, ctx: dict) -> dict:
    return message({"kind": "starting", **scene}, ctx)


def brb(scene: dict, ctx: dict) -> dict:
    return message({"kind": "brb", "countdown_min": 0, **scene}, ctx)


def ending(scene: dict, ctx: dict) -> dict:
    return message({"kind": "ending", "countdown_min": 0, **scene}, ctx)


# ---------------------------------------------------------------- vertical (1080x1920: TikTok, Shorts, Reels lives)


def vertical_split(scene: dict, ctx: dict) -> dict:
    """Content on top (16:9), camera below, brand strip between them."""
    cw, ch = ctx["canvas"]
    content = scene.get("content", "game")
    top = r(0, 0, cw, round(cw / W16))  # 1080x608
    cam_y = top[3] + 120
    cam = r(0, cam_y, cw, ch - cam_y)
    bg = [
        {"type": "backdrop", "rail_x": None, "glow": "center"},
        {"type": "text", "key": scene.get("text_key", "title"), "style": "title", "x": 48, "y": top[3] + 34, "w": cw - 96, "lines": 1},
    ]
    return {"slots": [slot(content, top), slot("camera", cam, "cover")], "bg": bg, "fg": None, "mic": True, "restart": False}


PRESETS = {
    "tutorial": tutorial,
    "screen_focus": fullscreen_pip,
    "fullscreen_pip": fullscreen_pip,
    "gameplay": gameplay,
    "gameplay_framed": gameplay_framed,
    "react": react,
    "react_pip": react_pip,
    "framed": framed,
    "camera_full": camera_full,
    "just_chatting": just_chatting,
    "side_by_side": side_by_side,
    "starting": starting,
    "brb": brb,
    "ending": ending,
    "message": message,
    "vertical_split": vertical_split,
}

VERTICAL_OK = {"camera_full", "vertical_split", "starting", "brb", "ending", "message", "fullscreen_pip", "screen_focus"}


def expand(scene: dict, ctx: dict) -> dict:
    preset = scene.get("preset")
    if scene.get("slots") is not None and not preset:
        # fully custom scene: the AI wrote slots and elements itself
        return {"slots": scene["slots"], "bg": scene.get("bg"), "fg": scene.get("fg"),
                "mic": scene.get("mic", True), "restart": scene.get("restart", False)}
    if preset not in PRESETS:
        raise ValueError(f"scene {scene.get('id')!r}: unknown preset {preset!r}; options: {', '.join(sorted(PRESETS))}")
    cw, ch = ctx["canvas"]
    if ch > cw and preset not in VERTICAL_OK:
        raise ValueError(f"scene {scene.get('id')!r}: preset {preset!r} is built for 16:9; on a vertical canvas use one of {sorted(VERTICAL_OK)} or custom slots")
    out = PRESETS[preset](scene.get("options", {}) | {k: v for k, v in scene.items() if k not in ("id", "name", "preset", "hotkey", "options")}, ctx)
    # per-scene overrides on top of the preset
    if scene.get("slots") is not None:
        out["slots"] = scene["slots"]
    for layer in ("bg", "fg"):
        extra = scene.get(f"extra_{layer}")
        if extra:
            out[layer] = (out[layer] or ([{"type": "backdrop", "rail_x": None}] if layer == "bg" else [])) + extra
    return out
