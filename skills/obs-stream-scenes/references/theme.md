# The theme contract

A scene is drawn by browser sources generated from `templates/layer.html`. That template places
elements at exact coordinates (from the scene presets) and gives them class names. **Everything about
how they look and move comes from the kit's theme**: `<kit>/theme/theme.css` and `<kit>/theme/theme.js`.
Write both for each client, from the brief. The theme folder may also hold images, SVGs or extra
fonts it references with relative paths (`url("../theme/motif.svg")`).

## CSS variables you get

Defined on `:root` from `studio.json` before your stylesheet loads:

| Variable | Meaning |
| -------- | ------- |
| `--bg`, `--text`, `--accent`, `--accent-2` | brand colors |
| `--bg-rgb`, `--text-rgb`, `--accent-rgb`, `--accent-2-rgb` | the same as `r, g, b` for `rgba(var(--accent-rgb), .4)` |
| `--font-sans`, `--font-display`, `--font-mono` | the three brand families (sans has 400 and ~600 loaded) |
| `--cw`, `--ch` | canvas size in px |
| `--frame-pad` | how far frames extend outside the captured box (default 10px); set it in your theme |
| `--live` | red for the live badge (override if the brand has its own) |

You may define your own variables too.

## Elements and their classes

All elements are absolutely positioned by the template; style their look, not their position (except
inside them). `body.frozen` is set during previews: stop CSS animations there.
`body[data-layer="bg|fg"]` and `body[data-scene="<id>"]` let you vary per layer or scene.

| Element | Markup | Notes |
| ------- | ------ | ----- |
| backdrop | `.backdrop` (full canvas) | Only in background layers. Paint it in `THEME.backdrop()`. Hints from presets: `e.glow` (`left`/`right`/`center`: where the content is not) and `e.rail_x` (a free vertical lane beside the text column, or null). |
| frame | `.frame` | Sits under a captured box (camera, screen, game), `--frame-pad` larger on each side. What shows is only its edge, so style it as a border/outline/glow. The capture covers the middle. |
| panel | `.panel` | Box under the chat or another widget. Translucent works well. |
| brand | `.brand.lg/.md/.sm` (+`.center`) containing `.logo` (img) or `.wordmark`, `.eyebrow`, `.product`, `.sub` | Size the pieces per variant. |
| text | `.t.label`, `.t.title`, `.t.caption`, `.t.headline`, `.t.display`, `.t.body` with `data-key` | Live texts. `.label` is small metadata, `.title` the lesson/stream title, `.caption` the line under content, `.headline` big heading, `.display` the waiting-screen hero. Line clamp is set by the preset. |
| rule | `.rule` | Thin horizontal divider (width set by preset; give it a height). |
| foot | `.foot` with `.foot-label` (`.dot` + name) and `.foot-site` | Bottom line under the main box. |
| socials | `.socials` with `.social` items and `.sep` between them | Style the separator with `.sep::before { content: "·" }` or anything. |
| pill | `.pill.<anchor>` with `.dot`, `.label` (brand), `.ptext` (live text) | Lower-third over full-screen content. |
| badge | `.badge` with `i` and `span` | "Live" indicator. |
| countdown | `.countdown` (`.done` when it reaches zero) | Text `MM:SS`, then the "soon" string. |

## theme.js

```js
window.THEME = {
  // paint the background (gradients, SVG motifs, canvas...) inside `node`
  backdrop(node, element, ctx) {},
  // optional: called for every element after it is added (add children, wrappers, attributes)
  decorate(node, element, ctx) {},
  // optional: called once after all elements exist
  after(stage, ctx) {},
  // optional: reaction when a live text changes (a short flash, a slide...)
  textChanged(node, key, ctx) {},
  // optional: custom element types usable in custom scenes: { type: "ticker", ... }
  elements: { ticker(element, ctx) { const n = document.createElement('div'); /* ... */ return n; } },
};
```

`ctx` has `canvas: [w, h]`, `frozen` (true in previews: render a representative still frame and start
no loops), `css(name)` to read a CSS variable, `data` (brand, texts, socials, strings) and `stage`.

## Designing it well

- **Start from the motif in the brief**, not from a gradient. One idea, executed with care, reads as
  a brand: lit cities connected by lines, a film strip, a racing line, chalk strokes, a sound wave,
  a blueprint grid, paper texture, pixel dither. Draw it with SVG or CSS.
- **Hierarchy over decoration.** The captured content is the star; frames and texts support it.
  Waiting screens (starting, brb, ending) are where the brand can be loud.
- **Motion budget.** Around content: one slow movement at most (8-15 s loops, low contrast). Waiting
  screens: livelier, still loopable without a visible jump. Always ease (`ease-in-out`, cubic), never
  linear for UI movement except constant scrolls. Respect `ctx.frozen` and `body.frozen`.
- **OBS performance.** Browser sources render on the GPU in every frame they are visible. Prefer CSS
  transforms/opacity and SVG; avoid huge blur filters animated every frame, big canvases at 60 fps,
  or video files as backgrounds unless the user asks.
- **Readable after compression.** Text 14 px minimum, 2 px lines for anything important, contrast per
  `brand-study.md`.
- **Respect the safe areas** the presets leave (40 px margins). If your frame style is thicker than
  `--frame-pad` + 10 px, increase `--frame-pad` instead of overflowing.
- **Logo on the background**: if the logo is dark-on-transparent and the background is dark, ask for
  the light version or use `.wordmark` text; never let the logo disappear.

## Checklist before showing previews

1. Nothing in the theme comes from another client or from an example without a reason in the brief.
2. Fonts and colors match the chosen direction.
3. Every element type the scenes use is styled (open each preview PNG).
4. Frozen previews show the motif in a good state (not mid-transition, not empty).
5. The theme works on every scene: tutorial columns, full-screen pips, waiting screens.
