# Studying the client

The goal is a design that a viewer would recognize as *this* client's even without the logo. That
only happens when every choice (type, color, shape, motion, tone of the texts) traces back to
something true about the client. Spend real time here; it is the difference between a custom studio
and a template with a logo pasted on it.

## 1. Gather evidence

Run the scanner first; it gives you facts instead of guesses:

```
python scripts/inspect_brand.py <kit> --url https://client.com --url https://client.com/sobre --logo path/to/logo.svg
```

Then look, don't just read:

- **The site screenshots** (`research/site-*-fold.png`, `site-*-page.png`): mood, density, how
  photos are treated, button shapes, corner radius, spacing, whether it is loud or calm.
- **Fonts actually used**: `@font-face` and Google Fonts lines are the strongest signal. If the brand
  uses a paid font that is not on Google Fonts, ask the user for the files (they go in `fonts.files`)
  or pick the closest free relative and say so.
- **Colors actually used**: CSS variables and the most used values. Separate them into background
  candidates, text, one or two accents. The logo palette confirms which accent is "theirs".
- **Social profiles**: banner, avatar, recent thumbnails, how they write captions. Thumbnails show the
  visual language the audience already associates with the creator.
- **Existing videos or lives** (if they have them): framing, where the camera sits, what their screen
  usually shows, how long they talk vs. show.
- **Their niche**: what do the best channels in this niche look like, and where can this client stand
  out instead of blending in? A finance educator and a horror-game streamer need opposite moods.

If the client has no site or brand (common with new streamers), the evidence is the interview: the
games or topics, the audience, the three adjectives, the references they like and dislike, their
personality on camera. Ask for 2 or 3 links of looks they admire.

## 2. Write the brief

Save `<kit>/research/brief.md`:

```markdown
# Brief: <client>

## Who
One paragraph: what they do, for whom, how they talk on camera.

## Audience
Age range, where they watch (phone, TV, desktop), what they expect.

## Evidence
- Site: fonts X and Y, background #..., accents #... and #..., photography of ..., radius ..., mood ...
- Logo: shape, colors (#... 60%, #... 25%), works on dark? on light?
- Socials/thumbnails: ...
- Niche: what everyone does; where this client can differ.

## Personality
Three adjectives, and what each means visually.

## Keep / avoid
- Keep: ...
- Avoid: ... (things the client dislikes, clichés of the niche, anything that fights the content)

## Directions
### A: <name>
Palette (hex with roles), type pairing (sans / display / mono), shapes (corners, lines, frames),
motif (one idea taken from the brand), motion (what moves, how fast, where), why it fits (evidence).
### B: <name>
...
### C (optional): <name>
...
```

## 3. Directions must really differ

Two directions that are the same layout in two colors are one direction. Vary at least three of:
palette temperature, type personality (geometric, humanist, grotesk, serif, condensed, mono-heavy),
shape language (round, sharp, cut corners, outlines, solid blocks), density, and motion character
(still, slow drift, rhythmic, energetic). One direction can stay close to the current brand; another
can push it.

Tie every direction to evidence, for example:

- "The site hero is the night Earth with lit cities → motif: points of light connected by thin lines,
  drifting slowly behind the lesson title."
- "Thumbnails use thick yellow outlines and bold condensed type → frames with a solid 6 px yellow
  stroke, condensed display type for titles."
- "Calm, premium real-estate audience → no particles, no glitch; one slow gradient shift."

## 4. Present and decide

Show the user each direction in 3-4 lines (palette as hex with names, fonts, the motif, the motion).
If they hesitate, build two quick previews (two themes, same scenes) and let them compare. Record the
choice and any tweaks at the end of `brief.md`, then move on to the scene plan.

## Readability checks before you commit

- Text over background at least 7:1, accent text at least 4.5:1 (`build_kit.py` warns).
- Smallest text on screen at least 14 px on a 1920x1080 canvas; viewers often watch at half size.
- Thin hairlines (1 px) and fine grain look great in a PNG and turn to mush after streaming
  compression; keep important lines 2 px or more.
- Avoid pure #000 / #fff fields that clip on some screens; near-black and off-white compress better.
