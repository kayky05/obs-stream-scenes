#!/usr/bin/env python3
"""Build a branded OBS scene kit from <kit>/studio.json.

    python build_kit.py <kit_dir> [--offline]

Reads <kit_dir>/studio.json (schema: references/config.md), fills in the defaults, downloads the
fonts, expands every scene preset into exact geometry, renders one or two browser-source layers per
scene and writes <kit_dir>/studio.lock.json.

studio.lock.json is the single source of truth: configure_obs.py, hotkeys.py and preview.py read it,
so the HTML frames and the OBS source positions always agree.

Safe to re-run after any change. Live texts in <kit_dir>/text/*.txt are created once and never
overwritten, because the user edits them between lessons or streams.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import presets  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
THEMES = SKILL_DIR / "examples"  # each example kit carries its theme in <example>/theme
USER_AGENT = "obs-stream-scenes/1.0"

LANG = {
    "pt": {
        "sources": {"mic": "Microfone", "desktop": "Áudio do PC", "camera": "Câmera", "camera2": "Câmera 2", "screen": "Tela do PC",
                    "game": "Jogo", "console": "Console", "window": "Janela", "browser": "Navegador", "chat": "Chat", "alerts": "Alertas"},
        "texts": {"label": "MÓDULO 01  ·  AULA 01", "title": "Título", "react": "Reagindo a: ", "starting": "A live já vai começar",
                  "brb": "Já volto", "ending": "Obrigado por assistir"},
        "strings": {"live": "Ao vivo", "soon": "Já já"},
        "layers": {"bg": "fundo", "fg": "sobreposição"},
    },
    "es": {
        "sources": {"mic": "Micrófono", "desktop": "Audio del PC", "camera": "Cámara", "camera2": "Cámara 2", "screen": "Pantalla",
                    "game": "Juego", "console": "Consola", "window": "Ventana", "browser": "Navegador", "chat": "Chat", "alerts": "Alertas"},
        "texts": {"label": "MÓDULO 01  ·  CLASE 01", "title": "Título", "react": "Reaccionando a: ", "starting": "El directo empieza pronto",
                  "brb": "Vuelvo enseguida", "ending": "Gracias por ver"},
        "strings": {"live": "En vivo", "soon": "Ya casi"},
        "layers": {"bg": "fondo", "fg": "superposición"},
    },
    "en": {
        "sources": {"mic": "Microphone", "desktop": "Desktop audio", "camera": "Camera", "camera2": "Camera 2", "screen": "Screen",
                    "game": "Game", "console": "Console", "window": "Window", "browser": "Browser", "chat": "Chat", "alerts": "Alerts"},
        "texts": {"label": "MODULE 01  ·  LESSON 01", "title": "Title", "react": "Reacting to: ", "starting": "Starting soon",
                  "brb": "Be right back", "ending": "Thanks for watching"},
        "strings": {"live": "Live", "soon": "Any minute"},
        "layers": {"bg": "background", "fg": "overlay"},
    },
}

SOURCE_TYPES = {"camera", "screen", "game", "capture_card", "window", "browser"}
DEFAULT_SOURCE_TYPES = {"camera": "camera", "camera2": "camera", "screen": "screen", "game": "game",
                        "console": "capture_card", "window": "window", "chat": "browser", "alerts": "browser", "browser": "browser"}

DEFAULTS: dict = {
    "language": "pt-BR",
    "mode": "record",  # record | stream | both
    "platform": None,  # twitch | youtube | kick | tiktok | facebook | None
    "canvas": [1920, 1080],
    "brand": {"name": "Studio", "product": "", "eyebrow": "", "tagline": "", "site": "", "footer_label": "", "logo": None, "logo_width": 232},
    "socials": [],
    # no default look on purpose: colors, fonts and theme come from studying the client (SKILL.md, phase 2)
    "colors": {},
    "fonts": {"display_style": "normal", "display_weight": 700, "files": {}},
    "texts": {},
    "sources": {},
    "scenes": [],
    "hotkeys": {"record": "Ctrl+Alt+R", "stream": None},
    "obs": {"profile": None, "collection": None, "fps": None, "encoder": "nvenc", "recordings": None, "format": "hybrid_mp4",
            "quality": "HQ", "video_bitrate": None, "audio_bitrate": 160, "websocket_port": 4455},
    "devices": {"camera": ["Sony", "ZV", "iPhone", "Camo", "Iriun", "C920", "Webcam", "Cam Link"], "camera2": [],
                "console": ["Elgato", "Cam Link", "USB Video", "Capture"], "mic": ["Lark", "Hollyland", "Wireless", "Rode", "Shure"],
                "monitor": 0, "camera_resolution": "1920x1080"},
    "audio": {"noise_suppression": True, "compressor": True, "limiter": True, "desktop_audio": None},
}

PLATFORM_BITRATE = {"twitch": 6000, "kick": 8000, "youtube": 9000, "facebook": 6000, "tiktok": 6000}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kit", help="kit folder that holds studio.json")
    parser.add_argument("--offline", action="store_true", help="do not download fonts (use the files already in fonts/)")
    parser.add_argument("--theme-from", help="copy a starting theme into <kit>/theme when it has none yet: an example name "
                        f"({', '.join(sorted(p.name for p in THEMES.iterdir() if p.is_dir()))}) or a folder path")
    args = parser.parse_args()

    kit = Path(args.kit).expanduser().resolve()
    config_path = kit / "studio.json"
    if not config_path.exists():
        print(f"studio.json not found in {kit}. Write one first (examples/ has starting points).", file=sys.stderr)
        return 1
    cfg = deep_merge(DEFAULTS, json.loads(config_path.read_text(encoding="utf-8")))
    lang_code = cfg["language"].split("-")[0].lower()
    L = LANG.get(lang_code, LANG["en"])
    live = cfg["mode"] in ("stream", "both")
    canvas = [int(cfg["canvas"][0]), int(cfg["canvas"][1])]

    problems: list[str] = []
    resolve_theme(kit, args.theme_from, problems)
    colors = resolve_colors(cfg["colors"], problems)
    brand = resolve_brand(cfg["brand"], config_path.parent, kit, problems)
    fonts = resolve_fonts(cfg["fonts"], config_path.parent, kit / "fonts", args.offline, problems)
    declared = cfg.get("sources") or {}
    available = {k for k, v in declared.items()
                 if not ((v.get("type") or DEFAULT_SOURCE_TYPES.get(k)) == "browser" and k in ("chat", "alerts") and not v.get("url"))}
    used: set[str] = set()
    for scene in cfg["scenes"]:  # first pass: which sources do the scenes actually place?
        try:
            used |= {s["source"] for s in presets.expand(scene, {"canvas": canvas, "live": live, "sources": available})["slots"]}
        except (ValueError, KeyError, TypeError):
            pass  # reported in the second pass
    sources = resolve_sources(cfg, L, used, problems)
    if not cfg["scenes"]:
        problems.append("ERROR studio.json has no scenes. Add at least one (see references/scenes.md).")

    ctx = {"canvas": canvas, "live": live, "sources": sources}
    scenes = []
    used_text_keys: set[str] = set()
    seen_ids: set[str] = set()
    for i, scene in enumerate(cfg["scenes"]):
        sid = scene.get("id") or f"scene{i + 1}"
        if sid in seen_ids:
            problems.append(f"ERROR two scenes share the id {sid!r}")
        seen_ids.add(sid)
        try:
            spec = presets.expand(scene, ctx)
        except ValueError as exc:
            problems.append(f"ERROR {exc}")
            continue
        for s in spec["slots"]:
            if s["source"] not in sources:
                problems.append(f"ERROR scene {sid!r} uses source {s['source']!r}, which is not defined in 'sources' "
                                f"(defined: {', '.join(sources) or 'none'})")
            check_rect(f"scene {sid!r} slot {s['source']!r}", s["rect"], canvas, problems)
        for layer in ("bg", "fg"):
            for e in spec[layer] or []:
                if e.get("type") == "text":
                    used_text_keys.add(e["key"])
                elif e.get("type") == "pill" and e.get("key"):
                    used_text_keys.add(e["key"])
        if "alerts" in sources and scene.get("alerts", spec["mic"]):
            spec["slots"].append({"source": "alerts", "rect": [0, 0, *canvas], "fit": "contain", "z": "over"})
        scenes.append({"id": sid, "name": scene.get("name") or sid, "hotkey": scene.get("hotkey"), **spec})
    if any(p.startswith("ERROR") for p in problems):
        print("\n".join(problems), file=sys.stderr)
        return 1

    # live texts
    text_dir = kit / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    texts = {}
    for key in sorted(used_text_keys):
        path = text_dir / f"{key}.txt"
        if not path.exists():
            default = cfg["texts"].get(key, L["texts"].get(key, key))
            path.write_text(default + "\n", encoding="utf-8")
        texts[key] = first_line(path)

    # render layers
    overlays = kit / "overlays"
    overlays.mkdir(parents=True, exist_ok=True)
    for old in overlays.glob("*.html"):
        old.unlink()
    template = (TEMPLATES / "layer.html").read_text(encoding="utf-8")
    common = theme_values(cfg, colors, fonts, canvas)
    for sc in scenes:
        sc["files"] = {}
        for layer in ("bg", "fg"):
            if not sc[layer]:
                continue
            data = {
                "canvas": canvas, "elements": sc[layer], "texts": texts, "socials": cfg["socials"],
                "strings": L["strings"], "layer": layer, "scene": sc["id"],
                "brand": {"name": brand.get("name"), "product": brand.get("product"), "eyebrow": brand.get("eyebrow"),
                          "tagline": brand.get("tagline"), "site": brand.get("site"), "footer_label": brand["footer_label"],
                          "logo": brand.get("logo_file"), "logo_width": int(brand.get("logo_width", 232))},
            }
            values = {**common, "TITLE": html.escape(f"{brand['footer_label']}: {sc['name']} ({layer})"),
                      "BODY_BG": "var(--bg)" if layer == "bg" else "transparent",
                      "DATA_JSON": json.dumps(data, ensure_ascii=False).replace("</", "<\\/")}
            path = overlays / f"{slug(sc['id'])}-{layer}.html"
            path.write_text(fill(template, values, "layer.html"), encoding="utf-8")
            sc["files"][layer] = str(path)

    footer = brand["footer_label"]
    obs_cfg = dict(cfg["obs"])
    obs_cfg["profile"] = obs_cfg["profile"] or footer
    obs_cfg["collection"] = obs_cfg["collection"] or footer
    obs_cfg["recordings"] = str(Path(obs_cfg["recordings"]).expanduser()) if obs_cfg["recordings"] else str(Path.home() / "Videos" / footer)
    has_game = any(s["type"] in ("game", "capture_card") for s in sources.values())
    obs_cfg["fps"] = obs_cfg["fps"] or (60 if has_game else 30)
    if live and not obs_cfg["video_bitrate"]:
        obs_cfg["video_bitrate"] = PLATFORM_BITRATE.get(cfg["platform"] or "", 6000)
    audio = dict(cfg["audio"])
    if audio["desktop_audio"] is None:
        # game, react and live streams need the PC sound; a recorded screen lesson does not
        audio["desktop_audio"] = live or has_game or any(s["type"] in ("window", "browser") and sid not in ("chat", "alerts") for sid, s in sources.items())

    lock = {
        "generated_by": "obs-stream-scenes build_kit.py",
        "kit": str(kit), "language": cfg["language"], "mode": cfg["mode"], "platform": cfg["platform"],
        "canvas": {"w": canvas[0], "h": canvas[1]},
        "sources": sources,
        "mic_name": L["sources"]["mic"], "desktop_name": L["sources"]["desktop"], "layer_names": L["layers"],
        "scenes": scenes,
        "hotkeys": cfg["hotkeys"],
        "obs": obs_cfg, "devices": cfg["devices"], "audio": audio,
        "text_dir": str(text_dir),
        "brand": {"footer_label": footer},
    }
    (kit / "studio.lock.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
    write_kit_readme(kit, lang_code, lock)

    for p in problems:
        print(p)
    print(f"Kit built in {kit}")
    for sc in scenes:
        layers = "+".join(k for k in ("bg", "fg") if sc[k]) or "no layers"
        print(f"  {sc['name']:<24} {len(sc['slots'])} sources, {layers}{', hotkey ' + sc['hotkey'] if sc.get('hotkey') else ''}")
    print(f"  live texts: {', '.join(sorted(texts)) or 'none'} (edit {text_dir})")
    return 0


# ------------------------------------------------------------------ config resolution


def deep_merge(base: dict, over: dict) -> dict:
    out = json.loads(json.dumps(base))
    for key, value in (over or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict) and key != "sources":
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def check_rect(label: str, rect: list[int], canvas: list[int], problems: list[str]) -> None:
    x, y, w, h = rect
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > canvas[0] or y + h > canvas[1]:
        problems.append(f"ERROR {label} rect {rect} is outside the {canvas[0]}x{canvas[1]} canvas")


def resolve_sources(cfg: dict, L: dict, used: set[str], problems: list[str]) -> dict:
    """Every scene slot points at a source id. A source is created once in OBS and reused by every scene."""
    out: dict = {}
    declared = cfg.get("sources") or {}
    for sid in sorted(used | set(declared)):
        spec = dict(declared.get(sid) or {})
        stype = spec.get("type") or DEFAULT_SOURCE_TYPES.get(sid)
        if stype not in SOURCE_TYPES:
            problems.append(f"ERROR source {sid!r} needs a type: one of {', '.join(sorted(SOURCE_TYPES))}")
            continue
        if stype == "browser" and not spec.get("url") and sid in ("chat", "alerts"):
            # chat or alerts without a URL yet: leave them out instead of placing an empty box
            if sid in declared:
                problems.append(f"WARN source {sid!r} has no url yet; it is skipped until you add one")
            continue
        spec["type"] = stype
        spec["name"] = spec.get("name") or L["sources"].get(sid, sid)
        if stype == "camera":
            spec.setdefault("hint", cfg["devices"].get(sid) or (cfg["devices"]["camera"] if sid == "camera" else []))
        if stype == "capture_card":
            spec.setdefault("hint", cfg["devices"].get("console") or [])
        if stype == "screen":
            spec.setdefault("monitor", cfg["devices"]["monitor"])
        out[sid] = spec
    return out


def hex_rgb(value: str) -> tuple[int, int, int]:
    h = value.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(value)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def luminance(rgb: tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def resolve_theme(kit: Path, theme_from: str | None, problems: list[str]) -> None:
    theme = kit / "theme"
    if theme_from and not (theme / "theme.css").exists():
        src = THEMES / theme_from / "theme" if (THEMES / theme_from / "theme").is_dir() else Path(theme_from).expanduser()
        if not (src / "theme.css").exists():
            problems.append(f"ERROR --theme-from {theme_from!r}: no theme.css there")
            return
        shutil.copytree(src, theme, dirs_exist_ok=True)
        problems.append(f"NOTE copied the {theme_from!r} theme into {theme} as a starting point. Rewrite it for this client "
                        f"before showing previews: it still carries the look of the brand it was made for.")
    for name in ("theme.css", "theme.js"):
        if not (theme / name).exists():
            problems.append(f"ERROR {theme / name} is missing. Write the client's theme (references/theme.md) "
                            f"or start from an example with --theme-from.")


def resolve_colors(colors: dict, problems: list[str]) -> dict:
    colors = dict(colors)
    if "accent_2" not in colors and "glow" in colors:
        colors["accent_2"] = colors["glow"]
    colors.setdefault("accent_2", colors.get("accent", "#000000"))
    out = {}
    for key in ("background", "text", "accent", "accent_2"):
        try:
            out[key] = hex_rgb(colors[key])
        except (KeyError, ValueError):
            problems.append(f"ERROR colors.{key} must be a hex color from the brand study (e.g. #e8d3a6), got {colors.get(key)!r}")
            out[key] = (0, 0, 0)
    c_text = contrast(out["text"], out["background"])
    c_acc = contrast(out["accent"], out["background"])
    if c_text < 7:
        problems.append(f"WARN colors.text on colors.background is {c_text:.1f}:1; aim for 7:1, video compression eats contrast")
    if c_acc < 4.5:
        problems.append(f"WARN colors.accent on colors.background is {c_acc:.1f}:1; small accent text may blur after upload")
    return {
        **{k: "#%02x%02x%02x" % v for k, v in out.items()},
        "rgb": {k: ", ".join(str(c) for c in v) for k, v in out.items()},
    }


def resolve_brand(brand: dict, config_dir: Path, kit: Path, problems: list[str]) -> dict:
    out = dict(brand)
    out["footer_label"] = brand.get("footer_label") or " ".join(x for x in (brand.get("name"), brand.get("product")) if x)
    out["logo_file"] = None
    logo = brand.get("logo")
    if logo:
        src = Path(logo) if Path(logo).is_absolute() else (config_dir / logo).resolve()
        if not src.exists():
            problems.append(f"ERROR brand.logo not found: {src}")
        elif src.suffix.lower() not in (".svg", ".png", ".webp", ".jpg", ".jpeg"):
            problems.append(f"ERROR brand.logo must be .svg, .png, .webp or .jpg, got {src.suffix}")
        else:
            dest_dir = kit / "brand"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / ("logo" + src.suffix.lower())
            if src.resolve() != dest.resolve():
                shutil.copyfile(src, dest)
            out["logo_file"] = f"../brand/{dest.name}"
    return out


def fontsource_id(family: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def resolve_fonts(fonts: dict, config_dir: Path, dest: Path, offline: bool, problems: list[str]) -> dict:
    """Return {role: {"family", "file", "weight", "style"}} for sans-400, sans-600, display and mono."""
    dest.mkdir(parents=True, exist_ok=True)
    missing = [k for k in ("sans", "display", "mono") if not fonts.get(k)]
    if missing:
        problems.append(f"ERROR fonts.{', fonts.'.join(missing)} not set. Pick them from the brand study (the site's own fonts, "
                        f"or a pairing that matches its personality), not from habit. See references/theme.md.")
        return {}
    roles = {
        "sans-400": (fonts["sans"], 400, "normal"),
        "sans-600": (fonts["sans"], 600, "normal"),
        "display": (fonts["display"], int(fonts.get("display_weight", 400)), fonts.get("display_style", "normal")),
        "mono": (fonts["mono"], 400, "normal"),
    }
    custom = fonts.get("files") or {}
    out: dict = {}
    licenses: dict[str, str] = {}
    for role, (family, weight, style) in roles.items():
        if role in custom:
            src = (config_dir / custom[role]).resolve()
            if not src.exists():
                problems.append(f"ERROR fonts.files.{role} not found: {src}")
                continue
            target = dest / f"{role}{src.suffix.lower()}"
            if src != target.resolve():
                shutil.copyfile(src, target)
            out[role] = {"family": family, "file": target.name, "weight": weight, "style": style}
            licenses[family] = "supplied by the user"
            continue
        fid = fontsource_id(family)
        if not offline:
            try:
                meta = json.loads(http_get(f"https://api.fontsource.org/v1/fonts/{fid}"))
                weights = meta.get("weights") or [weight]
                weight = min(weights, key=lambda w: (abs(w - weight), -w))
                if style not in (meta.get("styles") or [style]):
                    problems.append(f"WARN {family} has no {style} style; using normal")
                    style = "normal"
                licenses[family] = meta.get("license") or "see fontsource.org"
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    problems.append(f"ERROR font {family!r} is not on Fontsource/Google Fonts. Check the spelling on fonts.google.com "
                                    f"or pass the file in fonts.files.{role}")
                    continue
                problems.append(f"WARN Fontsource API error for {family!r} ({exc}); trying the file directly")
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                problems.append(f"WARN could not reach the Fontsource API for {family!r} ({exc}); trying the file directly")
        target = dest / f"{fid}-{weight}-{style}.ttf"
        if not target.exists():
            if offline:
                problems.append(f"ERROR --offline and {target.name} is missing")
                continue
            url = f"https://cdn.jsdelivr.net/fontsource/fonts/{fid}@latest/latin-{weight}-{style}.ttf"
            try:
                target.write_bytes(http_get(url))
            except (urllib.error.URLError, TimeoutError) as exc:
                problems.append(f"ERROR could not download {family} {weight} {style} ({url}): {exc}")
                continue
        out[role] = {"family": family, "file": target.name, "weight": weight, "style": style}
    lines = ["# Fonts in this kit", ""] + [f"- **{f}**: {lic} (https://fontsource.org/fonts/{fontsource_id(f)})" for f, lic in licenses.items()]
    (dest / "LICENSES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def first_line(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig").strip()
    return text.splitlines()[0].strip() if text else ""


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "scene"


# ------------------------------------------------------------------ rendering


def font_faces(fonts: dict) -> str:
    names = {"sans-400": ("Brand Sans", 400), "sans-600": ("Brand Sans", 600), "display": ("Brand Display", None), "mono": ("Brand Mono", 400)}
    rules = []
    for role, f in fonts.items():
        family, css_weight = names[role]
        rules.append(f'  @font-face {{ font-family: "{family}"; src: url("../fonts/{f["file"]}"); '
                     f'font-weight: {css_weight or f["weight"]}; font-style: {f["style"]}; }}')
    return "\n".join(rules)


def theme_values(cfg: dict, colors: dict, fonts: dict, canvas: list[int]) -> dict:
    return {
        "LANG": html.escape(cfg["language"]),
        "FONT_FACES": font_faces(fonts),
        "C_BG": colors["background"], "C_TEXT": colors["text"], "C_ACCENT": colors["accent"], "C_ACCENT2": colors["accent_2"],
        "C_BG_RGB": colors["rgb"]["background"], "C_ACCENT_RGB": colors["rgb"]["accent"],
        "C_ACCENT2_RGB": colors["rgb"]["accent_2"], "C_TEXT_RGB": colors["rgb"]["text"],
        "CW": canvas[0], "CH": canvas[1],
    }


def fill(template: str, values: dict, name: str) -> str:
    def sub(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(f"{name}: no value for {{{{{key}}}}}")
        return str(values[key])
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", sub, template)


def write_kit_readme(kit: Path, lang: str, lock: dict) -> None:
    template = TEMPLATES / ("KIT_README.pt.md" if lang == "pt" else "KIT_README.en.md")
    rows = "\n".join(f"| {s['name']} | {s.get('hotkey') or '-'} |" for s in lock["scenes"])
    texts = "\n".join(f"- `text/{p.name}`" for p in sorted(Path(lock["text_dir"]).glob("*.txt"))) or "-"
    hk = lock["hotkeys"]
    values = {
        "NAME": lock["brand"]["footer_label"], "KIT": lock["kit"], "SCENES": rows, "TEXTS": texts,
        "HK_RECORD": hk.get("record") or "-", "HK_STREAM": hk.get("stream") or "-",
        "RECORDINGS": lock["obs"]["recordings"], "SCRIPTS": str(Path(__file__).resolve().parent),
    }
    (kit / "README.md").write_text(fill(template.read_text(encoding="utf-8"), values, template.name), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
