# Scenes: presets, recipes and custom layouts

A scene in `studio.json` names a preset and a few options. `scripts/presets.py` turns it into exact
geometry: which sources go where (slots) and which elements the browser layers draw. Read the
docstrings there for the precise numbers. Canvas is 1920x1080 unless noted.

## Presets

| Preset | On screen | Options (default) | Sources used |
| ------ | --------- | ----------------- | ------------ |
| `tutorial` | Screen in a big 16:9 frame, camera in a small 4:3 frame, side column with brand, lesson label and title | `camera_side` (left), `content` (screen), `label_key` (label), `title_key` (title) | screen, camera |
| `screen_focus` / `fullscreen_pip` | Content fills the canvas, camera in a corner, pill with a live text | `content` (screen), `camera_corner` (bottom-right), `camera_shape` square/wide/none (square), `camera_size` (240 square, 432 wide), `pill_key` (title, or null), `badge` (false), `chat` (false) | content, camera |
| `gameplay` | Game full screen, wide camera bottom-left, live badge when streaming | same as fullscreen_pip; defaults content game, wide, bottom-left, no pill | game, camera |
| `react_pip` | Video full screen, wide camera bottom-right, pill "reacting to" | defaults content window, wide 480, pill_key react | window, camera |
| `framed` | Content in a big frame, side column with camera on top and chat (or brand) below, caption and socials under the content | `content` (window), `content_side` (left), `chat` (true if a chat source exists), `text_key` | content, camera, chat |
| `gameplay_framed` | framed with the game | content game, text_key title | game, camera, chat |
| `react` | framed with the video window | content window, text_key react | window, camera, chat |
| `camera_full` | Camera fills the canvas | `camera` (camera), `lower_third` (false), `pill_key` (title) | camera |
| `just_chatting` | Camera big in a frame, chat column, caption and socials | `text_key` (title); falls back to camera_full + lower third without chat | camera, chat |
| `side_by_side` | Two equal 16:9 boxes, heading above, footer below | `left` (window), `right` (camera), `text_key` (title) | both |
| `starting` | Brand, big headline, countdown, socials | `countdown_min` (5), `text_key` (starting), `mic` (false) | none |
| `brb` | Brand, headline, socials | `countdown_min` (0), `text_key` (brb) | none |
| `ending` | Brand, headline, socials | `text_key` (ending) | none |
| `vertical_split` | 1080x1920 canvas: content on top, title strip, camera below | `content` (game), `text_key` | content, camera |

On a vertical canvas (`"canvas": [1080, 1920]`) only `camera_full`, `vertical_split`,
`fullscreen_pip`, `screen_focus` and the message screens apply. OBS has one canvas per profile: if a
client needs horizontal and vertical, make two kits (two profiles and collections).

## Recipes by use

Pick, then trim to what the user will really switch to.

- **Recorded course or tutorial**: `tutorial` (main), `screen_focus` (details), `camera_full` (intro,
  explanations). No waiting screens. Desktop audio off. 30 fps.
- **Live class or webinar**: `starting`, `tutorial` or `framed` with `content: screen`, `camera_full`
  with `lower_third`, `brb`, `ending`. Chat on screen only if the audience is engaged.
- **PC gameplay live**: `starting`, `gameplay` (main), `gameplay_framed` (chatting between rounds),
  `just_chatting`, `brb`, `ending`. Desktop audio on, 60 fps.
- **Console gameplay**: as PC, with `"content": "console"` (capture card source).
- **React**: `starting`, `react` (main), `react_pip` (when the video needs the whole screen),
  `just_chatting`, `ending`. Mention copyright/fair-use risk to the user once; do not lecture.
- **Podcast or interview**: `side_by_side` with `left: camera`, `right: camera2`, `camera_full` per
  host (`camera: camera2` for the second), `starting`, `ending`.
- **Just chatting / IRL at the desk**: `starting`, `just_chatting`, `camera_full` with `lower_third`,
  `brb`, `ending`.
- **Sales live**: `starting` (countdown builds anticipation), `camera_full` with `lower_third`
  (pill_key: offer), `framed` with `content: screen` for showing the product, `ending` with the CTA
  as the headline.

## Sources

Scene slots point to source ids. Each source is created once in OBS and reused in every scene.

| id (default type) | What it is |
| ----------------- | ---------- |
| `camera`, `camera2` (camera) | Video capture device, picked by name hints in `devices.camera` / `devices.camera2` |
| `screen` (screen) | Monitor capture, `devices.monitor` index |
| `game` (game) | Windows game capture (any full-screen game); screen capture elsewhere |
| `console` (capture_card) | Capture card, hints in `devices.console` |
| `window` (window) | Window capture; the user picks the window in OBS |
| `browser` (browser) | Any web page: `{"type": "browser", "url": "..."}` |
| `chat` (browser) | Chat widget or popout URL (see obs-setup.md). Without a URL it is left out. |
| `alerts` (browser) | Alert box URL; placed full-canvas on top of every scene with a mic. |

Declare extra or renamed sources in `"sources"`, e.g. `"cam_top": {"type": "camera", "hint": ["Brio"]}`.

## Custom scenes

When no preset fits (a split for a cooking show, a three-person panel, a product close-up), write the
scene by hand. Omit `preset` and give `slots`, `bg` and/or `fg`:

```json
{
  "id": "cooking", "name": "Bancada", "hotkey": "Ctrl+Alt+5", "mic": true,
  "slots": [
    { "source": "camera", "rect": [40, 60, 1220, 686], "fit": "cover", "z": "under" },
    { "source": "camera2", "rect": [1300, 60, 580, 435], "fit": "cover", "z": "under" }
  ],
  "bg": [
    { "type": "backdrop", "glow": "center", "rail_x": null },
    { "type": "frame", "rect": [40, 60, 1220, 686] },
    { "type": "frame", "rect": [1300, 60, 580, 435] },
    { "type": "text", "key": "recipe", "style": "headline", "x": 1300, "y": 540, "w": 580, "lines": 3 },
    { "type": "socials", "x": 40, "y": 800, "w": 1220 }
  ]
}
```

Rules: `rect` is `[x, y, w, h]` inside the canvas; frames use the same rect as the slot they surround;
`fit: cover` for cameras, `contain` for screens/games/videos; `z: over` only for things that must sit
above a full-screen content plus its foreground layer (a corner camera, a chat over a game). Keep
40 px margins, 16:9 content boxes and 4:3 or 16:9 camera boxes. You can also start from a preset and
override: `slots` replaces its slots, `extra_bg` / `extra_fg` add elements. Theme-defined element types
(`THEME.elements`) work in `bg`/`fg` too.

Element types: `backdrop`, `frame`, `panel`, `brand`, `text`, `rule`, `foot`, `socials`, `pill`,
`badge`, `countdown` (fields in `references/theme.md` and `templates/layer.html`).
