#!/usr/bin/env python3
"""Collect hard evidence about a client's brand before designing anything.

    python inspect_brand.py <kit_dir> --url https://client.com [--url https://client.com/about] [--logo logo.png ...]

For each URL: fetches the page and its stylesheets, then reports
  - fonts actually used (font-family declarations, Google Fonts links, @font-face rules)
  - colors actually used (CSS custom properties, most frequent hex/rgb values, <meta name=theme-color>)
  - title, description, og:image, icons, and links to the client's social profiles
  - a screenshot of the page (needs Chrome or Edge), so you can look at it
For each logo (given, or the site's og:image / apple-touch-icon): the dominant colors.

Writes everything to <kit_dir>/research/ (brand-scan.json, screenshots, downloaded images) and prints a
summary. It gathers facts; the design decisions are yours (SKILL.md, phase 2).
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
SOCIAL = {
    "instagram": r"instagram\.com/[\w.]+", "youtube": r"youtube\.com/(?:@[\w.-]+|c/[\w.-]+|channel/[\w-]+)",
    "twitch": r"twitch\.tv/[\w]+", "tiktok": r"tiktok\.com/@[\w.]+", "x": r"(?:twitter|x)\.com/[\w]+",
    "kick": r"kick\.com/[\w]+", "linkedin": r"linkedin\.com/(?:company|in)/[\w-]+", "facebook": r"facebook\.com/[\w.]+",
}
GENERIC_FONTS = {"sans-serif", "serif", "monospace", "system-ui", "inherit", "initial", "unset", "cursive", "fantasy",
                 "-apple-system", "blinkmacsystemfont", "segoe ui", "roboto", "helvetica neue", "arial", "helvetica",
                 "ui-sans-serif", "ui-monospace", "ui-serif", "apple color emoji", "segoe ui emoji", "segoe ui symbol",
                 "noto color emoji", "var", "emoji", "math", "fangsong", "sfmono-regular", "menlo", "monaco", "consolas",
                 "liberation mono", "courier new", "noto sans", "liberation sans", "times new roman", "georgia"}


def get(url: str, binary: bool = False, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if binary:
            return data
        charset = r.headers.get_content_charset() or "utf-8"
        return data.decode(charset, errors="replace")


def scan_css(css: str, fonts: collections.Counter, colors: collections.Counter, variables: dict, faces: set) -> None:
    for m in re.finditer(r"font-family\s*:\s*([^;}]+)", css, re.I):
        for fam in m.group(1).split(","):
            name = fam.strip().strip("'\"()! ").replace("important", "").strip().strip("'\"")
            if name and name.lower() not in GENERIC_FONTS and not name.startswith("var("):
                fonts[name] += 1
    for m in re.finditer(r"@font-face\s*{[^}]*?font-family\s*:\s*['\"]?([^;'\"}]+)", css, re.I):
        faces.add(m.group(1).strip())
    for m in re.finditer(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+", css):
        c = normalize_color(m.group(0))
        if c:
            colors[c] += 1
    for m in re.finditer(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\))", css):
        variables.setdefault(m.group(1), m.group(2).strip())


def normalize_color(text: str) -> str | None:
    text = text.strip()
    if text.startswith("#"):
        h = text[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return "#" + h[:6].lower()
    nums = re.findall(r"\d+", text)[:3]
    if len(nums) == 3:
        return "#%02x%02x%02x" % tuple(min(255, int(n)) for n in nums)
    return None


def meta(html_text: str, name: str) -> str | None:
    m = re.search(rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]*content=["\']([^"\']+)', html_text, re.I) or \
        re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:name|property)=["\']{re.escape(name)}["\']', html_text, re.I)
    return html.unescape(m.group(1)) if m else None


def palette(path: Path, n: int = 6) -> list[dict]:
    try:
        from PIL import Image
    except ImportError:
        return [{"error": "pip install pillow to extract logo colors"}]
    img = Image.open(path).convert("RGBA")
    img.thumbnail((256, 256))
    data = img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()
    px = [p[:3] for p in data if p[3] > 200]
    if not px:
        return []
    solid = Image.new("RGB", (len(px), 1))
    solid.putdata(px)
    q = solid.quantize(colors=n * 2, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    total = sum(c for c, _ in q.getcolors())
    merged: list[list] = []  # [rgb, count]; near-identical shades are one brand color
    for count, i in sorted(q.getcolors(), reverse=True):
        rgb = tuple(pal[i * 3:i * 3 + 3])
        for m in merged:
            if sum((a - b) ** 2 for a, b in zip(m[0], rgb)) ** .5 < 28:
                m[1] += count
                break
        else:
            merged.append([rgb, count])
    merged.sort(key=lambda m: -m[1])
    return [{"hex": "#%02x%02x%02x" % m[0], "share": round(m[1] / total, 3)} for m in merged[:n]]


def rasterize_svg(svg: Path, out: Path) -> Path | None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from preview import find_browser
    browser = find_browser()
    if not browser:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp}",
                        "--window-size=800,400", "--default-background-color=00000000", f"--screenshot={out}", svg.resolve().as_uri()],
                       capture_output=True, timeout=60)
    return out if out.exists() else None


def screenshot(url: str, out: Path, size: str = "1440,2400") -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from preview import find_browser
    browser = find_browser()
    if not browser:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio", f"--user-data-dir={tmp}",
                        f"--window-size={size}", "--virtual-time-budget=6000", f"--screenshot={out}", url],
                       capture_output=True, timeout=90)
    return out.exists()


def scan_url(url: str, research: Path, idx: int) -> dict:
    out: dict = {"url": url}
    try:
        page = get(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"url": url, "error": str(exc)}
    fonts, colors, faces, variables = collections.Counter(), collections.Counter(), set(), {}
    for style in re.findall(r"<style[^>]*>(.*?)</style>", page, re.S | re.I):
        scan_css(style, fonts, colors, variables, faces)
    for attr in re.findall(r'style=["\']([^"\']+)', page):
        scan_css(attr, fonts, colors, variables, faces)
    sheets = re.findall(r'<link[^>]+rel=["\']?stylesheet["\']?[^>]*href=["\']([^"\']+)', page, re.I)
    sheets += re.findall(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']?stylesheet', page, re.I)
    google = set()
    for href in dict.fromkeys(sheets):
        full = urllib.parse.urljoin(url, html.unescape(href))
        if "fonts.googleapis.com" in full:
            for fam in re.findall(r"family=([^&:]+)", full):
                google.add(urllib.parse.unquote_plus(fam))
        try:
            scan_css(get(full, timeout=15), fonts, colors, variables, faces)
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue
    for fam in re.findall(r"fonts\.googleapis\.com/css2?\?[^\"']*family=([^&:\"']+)", page):
        google.add(urllib.parse.unquote_plus(fam))
    # next/font and similar inline the family names as CSS classes like __Inter_abc123
    for fam in re.findall(r"__([A-Z][A-Za-z]+(?:_[A-Z][A-Za-z]+)*)_[0-9a-f]{6}", page):
        fonts[fam.replace("_", " ")] += 1

    socials = {}
    for net, pattern in SOCIAL.items():
        found = sorted(set(re.findall(pattern, page, re.I)))
        if found:
            socials[net] = found[:3]
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    icons = re.findall(r'<link[^>]+rel=["\'](?:apple-touch-icon|icon|shortcut icon)["\'][^>]*href=["\']([^"\']+)', page, re.I)
    out.update({
        "title": html.unescape(title.group(1).strip()) if title else None,
        "description": meta(page, "description") or meta(page, "og:description"),
        "site_name": meta(page, "og:site_name"),
        "theme_color": meta(page, "theme-color"),
        "og_image": urllib.parse.urljoin(url, meta(page, "og:image")) if meta(page, "og:image") else None,
        "icons": [urllib.parse.urljoin(url, i) for i in icons][:4],
        "google_fonts": sorted(google),
        "font_faces": sorted(faces),
        "fonts_by_use": fonts.most_common(12),
        "color_variables": dict(list(variables.items())[:40]),
        "colors_by_use": colors.most_common(16),
        "socials": socials,
    })
    fold = research / f"site-{idx}-fold.png"   # what a visitor sees first
    tall = research / f"site-{idx}-page.png"   # more of the page: sections, cards, buttons
    shots = [str(f) for f, size in ((fold, "1440,900"), (tall, "1440,3200")) if screenshot(url, f, size)]
    if shots:
        out["screenshots"] = shots
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kit")
    p.add_argument("--url", action="append", default=[])
    p.add_argument("--logo", action="append", default=[])
    args = p.parse_args()
    research = Path(args.kit).expanduser().resolve() / "research"
    research.mkdir(parents=True, exist_ok=True)

    report: dict = {"pages": [], "images": []}
    for i, url in enumerate(args.url, 1):
        if not re.match(r"https?://", url):
            url = "https://" + url
        print(f"Scanning {url} ...")
        report["pages"].append(scan_url(url, research, i))

    images = [Path(l) for l in args.logo]
    for page in report["pages"]:
        for remote in [page.get("og_image"), *(page.get("icons") or [])[:1]]:
            if not remote:
                continue
            name = research / ("img-" + re.sub(r"[^\w.-]", "_", urllib.parse.urlparse(remote).path.split("/")[-1] or "image"))
            try:
                name.write_bytes(get(remote, binary=True))
                images.append(name)
            except (urllib.error.URLError, TimeoutError, ValueError):
                pass
    for img in images:
        src = img
        if img.suffix.lower() == ".svg":
            src = rasterize_svg(img, research / (img.stem + "-svg.png")) or img
        try:
            report["images"].append({"file": str(img), "palette": palette(src)})
        except Exception as exc:  # noqa: BLE001 - any unreadable image
            report["images"].append({"file": str(img), "error": str(exc)})

    (research / "brand-scan.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for page in report["pages"]:
        print(f"\n== {page['url']}")
        if page.get("error"):
            print("  could not load:", page["error"])
            continue
        print("  title:", page.get("title"))
        if page.get("description"):
            print("  description:", page["description"][:160])
        print("  google fonts:", ", ".join(page["google_fonts"]) or "-")
        print("  @font-face:", ", ".join(page["font_faces"][:8]) or "-")
        print("  fonts by use:", ", ".join(f"{f} ({n})" for f, n in page["fonts_by_use"][:6]) or "-")
        print("  theme-color:", page.get("theme_color") or "-")
        print("  color variables:", ", ".join(f"{k}={v}" for k, v in list(page["color_variables"].items())[:10]) or "-")
        print("  colors by use:", ", ".join(f"{c} ({n})" for c, n in page["colors_by_use"][:10]) or "-")
        print("  socials:", json.dumps(page["socials"], ensure_ascii=False) if page["socials"] else "-")
        for shot in page.get("screenshots", []):
            print("  screenshot:", shot, "(open it and look)")
    for img in report["images"]:
        print(f"\n== image {img['file']}")
        print("  palette:", ", ".join(f"{c['hex']} {c['share']:.0%}" for c in img.get("palette", []) if "hex" in c) or img.get("error"))
    print(f"\nSaved {research / 'brand-scan.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
