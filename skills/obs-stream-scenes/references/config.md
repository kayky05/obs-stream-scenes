# studio.json

One file per kit, at `<kit>/studio.json`. Paths inside it are relative to the kit folder.
`build_kit.py` fills defaults and writes the resolved result to `studio.lock.json` (do not edit that).

```jsonc
{
  "language": "pt-BR",            // scene/source names and default texts: pt, es or en
  "mode": "record",               // record | stream | both  (stream adds live badges, bitrate)
  "platform": "youtube",          // twitch | youtube | kick | tiktok | facebook | null (sets bitrate)
  "canvas": [1920, 1080],         // [1080, 1920] for vertical

  "brand": {
    "name": "Zuuuw",              // used as text wordmark when there is no logo
    "product": "Academy",         // optional big word (display font) under the logo
    "eyebrow": "Plataforma · Tutoriais",
    "tagline": "Aprenda a usar a plataforma,\ntela por tela.",
    "site": "zuuuw.com.br",
    "footer_label": "Zuuuw Academy", // default: name + product; also names the OBS profile/collection
    "logo": "brand/logo.svg",     // svg, png, webp or jpg, light version for dark backgrounds
    "logo_width": 232
  },
  "socials": ["@zuuuw", "youtube.com/@zuuuw"],

  // REQUIRED, from the brand study: no defaults on purpose
  "colors": { "background": "#121315", "text": "#eef1f7", "accent": "#e8d3a6", "accent_2": "#356ef3" },
  "fonts": {
    "sans": "Instrument Sans",    // any family on fonts.google.com / fontsource.org
    "display": "Instrument Serif",
    "display_style": "italic",    // normal | italic
    "display_weight": 400,
    "mono": "Geist Mono",
    "files": {}                   // brand-owned fonts: {"sans-400": "fonts-src/Brand-Regular.otf",
                                  //  "sans-600": "...", "display": "...", "mono": "..."}
  },

  "texts": { "label": "MÓDULO 01  ·  AULA 03", "title": "..." },  // initial live texts (text/<key>.txt)

  "sources": {                    // only to add or change sources; defaults cover camera, screen, game...
    "chat": { "type": "browser", "url": "https://www.twitch.tv/popout/<channel>/chat?popout=" },
    "camera2": { "type": "camera", "hint": ["Sony", "ZV-E10"] }
  },

  "scenes": [                     // order = order in OBS; the first is the starting scene
    { "id": "tutorial", "name": "Tutorial", "preset": "tutorial", "camera_side": "left", "hotkey": "Ctrl+Alt+1" }
  ],

  "hotkeys": { "record": "Ctrl+Alt+R", "stream": "Ctrl+Alt+S" },  // scene hotkeys live in each scene

  "obs": {
    "profile": null, "collection": null,   // default: brand.footer_label
    "fps": null,                  // default 60 with game/console sources, else 30
    "encoder": "nvenc",           // nvenc (NVIDIA) | amd | qsv (Intel) | x264 (CPU) | apple_h264 (Mac)
    "recordings": "~/Videos/Zuuuw Academy",
    "format": "hybrid_mp4",       // survives crashes; mkv on old OBS
    "quality": "HQ",              // Stream | HQ | Lossless
    "video_bitrate": null,        // default per platform when streaming (Twitch 6000, YouTube 9000...)
    "audio_bitrate": 160,
    "websocket_port": 4455
  },
  "devices": {
    "camera": ["Sony", "ZV", "iPhone", "Camo", "Iriun", "C920", "Webcam", "Cam Link"],  // name hints, in order
    "camera2": [], "console": ["Elgato", "Cam Link", "USB Video", "Capture"],
    "mic": ["Lark", "Hollyland", "Wireless", "Rode", "Shure"],
    "monitor": 0,                 // which monitor the screen source captures
    "camera_resolution": "1920x1080"
  },
  "audio": {
    "noise_suppression": true, "compressor": true, "limiter": true,
    "desktop_audio": null         // null = on for streams, games and react; off for recorded screen lessons
  }
}
```

## Scene entries

```jsonc
{
  "id": "game",                 // stable id: file names and preview names use it
  "name": "Gameplay",           // the name shown in OBS
  "preset": "gameplay",         // see references/scenes.md; omit for a fully custom scene
  "hotkey": "Ctrl+Alt+2",
  // any preset option at the top level, e.g. "camera_corner": "bottom-right", "chat": true
  // overrides: "slots": [...], "extra_bg": [...], "extra_fg": [...], "alerts": false
}
```

## What build_kit.py writes in the kit

```
<kit>/
  studio.json          you write it
  theme/               you write it (theme.css, theme.js, assets)
  research/            inspect_brand.py output + brief.md
  brand/logo.*         copied from brand.logo
  fonts/               downloaded or copied fonts + LICENSES.md
  text/<key>.txt       live texts (created once, never overwritten)
  overlays/<scene>-bg.html, <scene>-fg.html   generated, overwritten on every build
  studio.lock.json     generated, read by the other scripts
  preview/             preview.py output
  README.md            generated hand-off guide for the user
```
