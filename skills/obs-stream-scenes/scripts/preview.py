#!/usr/bin/env python3
"""Render a PNG preview of every scene in a kit, without OBS.

    python preview.py <kit_dir> [--sample camera=me.jpg --sample screen=app.png ...] [--scenes id1,id2]

Screenshots each browser layer with headless Chrome or Edge (animations frozen), then composites the
scene in OBS order: background layer, sources under, foreground layer, sources over. Sources are drawn
as labelled placeholders unless you pass a sample image for that source id.

Writes <kit_dir>/preview/<scene-id>.png and <kit_dir>/preview/all.png (contact sheet).
Needs Pillow (pip install pillow) and Chrome, Chromium or Edge.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    sys.exit("Pillow is missing: pip install pillow")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from obs_paths import load_lock  # noqa: E402


def find_browser() -> str | None:
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    candidates = {
        "Windows": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"],
        "Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                   "/Applications/Chromium.app/Contents/MacOS/Chromium",
                   "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
    }.get(platform.system(), [])
    for c in candidates:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def screenshot(browser: str, html: Path, out: Path, w: int, h: int, transparent: bool, profile: Path) -> None:
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--no-first-run",
           "--allow-file-access-from-files", "--force-device-scale-factor=1", f"--window-size={w},{h}",
           f"--user-data-dir={profile}", "--virtual-time-budget=3000", f"--screenshot={out}"]
    if transparent:
        cmd.append("--default-background-color=00000000")
    cmd.append(html.resolve().as_uri() + "?anim=0")
    subprocess.run(cmd, capture_output=True, timeout=90)
    if not out.exists():
        raise RuntimeError(f"browser did not write {out}")


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def placeholder(kind: str, label: str, w: int, h: int) -> Image.Image:
    img = Image.new("RGBA", (w, h), (40, 42, 48, 255))
    d = ImageDraw.Draw(img)
    if kind == "camera":
        img.paste((58, 62, 70, 255), (0, 0, w, h))
        cx, cy, s = w // 2, int(h * 0.42), min(w, h)
        d.ellipse((cx - s * .16, cy - s * .2, cx + s * .16, cy + s * .12), fill=(150, 156, 168, 255))
        d.ellipse((cx - s * .34, cy + s * .16, cx + s * .34, cy + s * .75), fill=(150, 156, 168, 255))
    elif kind == "game":
        for y in range(h):
            t = y / max(1, h - 1)
            d.line([(0, y), (w, y)], fill=(int(30 + 60 * t), int(20 + 30 * t), int(70 + 40 * (1 - t)), 255))
        d.polygon([(0, h), (w * .3, h * .55), (w * .55, h * .8), (w * .8, h * .45), (w, h * .7), (w, h)], fill=(18, 60, 52, 255))
        d.rectangle((w * .03, h * .04, w * .2, h * .08), fill=(230, 70, 70, 255))
    elif kind in ("window", "browser"):
        img.paste((12, 12, 14, 255), (0, 0, w, h))
        t = min(w, h) * .12
        d.polygon([(w / 2 - t * .6, h / 2 - t), (w / 2 - t * .6, h / 2 + t), (w / 2 + t, h / 2)], fill=(235, 235, 235, 255))
        d.rectangle((w * .04, h * .9, w * .96, h * .91), fill=(90, 90, 90, 255))
        d.rectangle((w * .04, h * .9, w * .38, h * .91), fill=(230, 60, 60, 255))
    elif kind == "screen":
        img.paste((244, 245, 248, 255), (0, 0, w, h))
        d.rectangle((0, 0, w, h * .07), fill=(255, 255, 255, 255))
        d.rectangle((0, h * .07, w * .16, h), fill=(232, 234, 240, 255))
        for i in range(3):
            x0 = w * (.2 + i * .26)
            d.rounded_rectangle((x0, h * .14, x0 + w * .23, h * .4), radius=12, fill=(255, 255, 255, 255), outline=(220, 222, 230, 255))
        d.rounded_rectangle((w * .2, h * .46, w * .95, h * .92), radius=12, fill=(255, 255, 255, 255), outline=(220, 222, 230, 255))
    elif kind == "chat":
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        f = font(max(14, w // 22))
        lines = [("ana_gg", "kkkkk que jogada"), ("leo.dev", "salve salve"), ("mari", "GG!!"), ("joao77", "qual o setup?"),
                 ("bia", "primeira vez aqui"), ("caio", "manda o link")]
        y = 16
        for user, msg in lines * 3:
            if y > h - 40:
                break
            d.text((18, y), user, font=f, fill=(255, 200, 90, 255))
            d.text((18 + d.textlength(user + "  ", font=f), y), msg, font=f, fill=(235, 235, 235, 255))
            y += int(f.size * 1.7)
        return img
    else:  # capture_card and anything else
        img.paste((34, 30, 46, 255), (0, 0, w, h))
    f = font(max(16, min(28, min(w, h) // 12)))
    tw = d.textlength(label, font=f)
    d.rounded_rectangle((w / 2 - tw / 2 - 16, h - f.size * 2.4, w / 2 + tw / 2 + 16, h - f.size * .8), radius=10, fill=(0, 0, 0, 150))
    d.text((w / 2 - tw / 2, h - f.size * 2.25), label, font=f, fill=(255, 255, 255, 230))
    return img


def fit_image(img: Image.Image, w: int, h: int, mode: str) -> Image.Image:
    img = img.convert("RGBA")
    if mode == "cover":
        return ImageOps.fit(img, (w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    c = ImageOps.contain(img, (w, h), Image.LANCZOS)
    canvas.paste(c, ((w - c.width) // 2, (h - c.height) // 2), c)
    return canvas


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kit")
    p.add_argument("--sample", action="append", default=[], help="source_id=image path, e.g. camera=me.jpg")
    p.add_argument("--scenes", help="comma-separated scene ids (default: all)")
    args = p.parse_args()

    lock = load_lock(args.kit)
    kit = Path(lock["kit"])
    W, H = lock["canvas"]["w"], lock["canvas"]["h"]
    samples = {}
    for s in args.sample:
        sid, _, path = s.partition("=")
        samples[sid] = Image.open(path)
    browser = find_browser()
    if not browser:
        print("Chrome, Chromium or Edge not found; set CHROME_PATH to the browser executable.", file=sys.stderr)
        return 1
    out_dir = kit / "preview"
    out_dir.mkdir(exist_ok=True)
    wanted = set(args.scenes.split(",")) if args.scenes else None

    rendered = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for sc in lock["scenes"]:
            if wanted and sc["id"] not in wanted:
                continue
            frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            layers = {}
            for layer in ("bg", "fg"):
                if layer in sc.get("files", {}):
                    shot = tmp / f"{sc['id']}-{layer}.png"
                    screenshot(browser, Path(sc["files"][layer]), shot, W, H, layer == "fg", tmp / "profile")
                    layers[layer] = Image.open(shot).convert("RGBA").resize((W, H))
            if "bg" in layers:
                frame.alpha_composite(layers["bg"])

            def paste(z: str) -> None:
                for slot in sc["slots"]:
                    if slot["z"] != z:
                        continue
                    sid = slot["source"]
                    src = lock["sources"].get(sid, {})
                    x, y, w, h = slot["rect"]
                    if sid == "alerts":
                        continue
                    kind = "chat" if sid == "chat" else src.get("type", "screen")
                    img = fit_image(samples[sid], w, h, slot["fit"]) if sid in samples else placeholder(kind, src.get("name", sid), w, h)
                    frame.alpha_composite(img, (x, y))

            paste("under")
            if "fg" in layers:
                frame.alpha_composite(layers["fg"])
            paste("over")
            out = out_dir / f"{sc['id']}.png"
            frame.convert("RGB").save(out)
            rendered.append((sc, out))
            print(f"{sc['name']}: {out}")

    if rendered:
        cols = 2 if len(rendered) > 1 else 1
        tw, th = W // 2, H // 2
        label_h = 44
        rows = (len(rendered) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw + (cols + 1) * 24, rows * (th + label_h) + (rows + 1) * 24), (24, 24, 28))
        d = ImageDraw.Draw(sheet)
        f = font(24)
        for i, (sc, path) in enumerate(rendered):
            cx, cy = 24 + (i % cols) * (tw + 24), 24 + (i // cols) * (th + label_h + 24)
            d.text((cx, cy + 6), f"{sc['name']}" + (f"   {sc['hotkey']}" if sc.get("hotkey") else ""), font=f, fill=(235, 235, 240))
            sheet.paste(Image.open(path).resize((tw, th), Image.LANCZOS), (cx, cy + label_h))
        sheet.save(out_dir / "all.png")
        print(f"contact sheet: {out_dir / 'all.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
