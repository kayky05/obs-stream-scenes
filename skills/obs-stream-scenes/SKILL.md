---
name: obs-stream-scenes
description: Designs and builds a complete, branded set of OBS scenes for a specific person or company, then configures OBS by itself. It interviews the user about what they do on camera (recorded lessons and tutorials, PC or console gameplay, react, podcast, just chatting, webinars, sales lives, vertical lives), studies the client's brand (site, logo, social profiles, niche, audience) and creates scenes that look like that client, not a template — starting soon, be right back and ending screens, gameplay with facecam, react layouts, tutorial screens, chat panels, live-editable titles — plus profile, sources, audio filters, recording and streaming settings, and hotkeys. Use it whenever someone wants stream overlays, OBS scenes, "telas de live", "cenas do OBS", a facecam frame, a starting-soon screen, a react or gameplay layout, a recording studio setup for courses, or to redo or rebrand their OBS, even if they never say "OBS".
---

# OBS stream scenes

You are going to act like the designer and the technician a streamer or a company would hire: first
understand what they do and who they are, then design scenes that only make sense for them, then
leave OBS ready to record or go live. Talk to the user in their language, in plain words; they are
usually creators, not engineers.

Everything lives in one **kit folder** per client. The pipeline:

```
interview ─► study the client ─► scene plan ─► theme + studio.json ─► build_kit.py ─► preview.py ─► approval
                                                                                                         │
            hotkeys.py ◄─ configure_obs.py ◄─ enable_websocket.py ◄─ install OBS ◄───────────────────────┘
```

Scripts are in `scripts/` next to this file; run them with `python` (Python 3.10+). Every script has
`--help`. Read the reference files when the phase below points to them.

| File | Read it when |
| ---- | ------------ |
| `references/brand-study.md` | Phase 2: how to study the client and write the brief |
| `references/scenes.md` | Phase 3: scene presets, recipes per use, custom layouts |
| `references/theme.md` | Phase 4: the theme contract and how to design one that is not generic |
| `references/config.md` | Phase 4: every field of `studio.json` |
| `references/obs-setup.md` | Phase 6: install, connect, configure, verify, equipment, troubleshooting |

## Phase 1: Interview

Ask before you assume. Use a structured question tool if your environment has one (for example
`AskUserQuestion`, up to 4 questions at a time with options); otherwise ask in chat, a few questions
per message. Skip anything the user already told you, and infer what you safely can. Three rounds are
usually enough:

**Round 1: the use.** What will they do on camera (one or more: lessons/tutorials, PC gameplay,
console gameplay, react, podcast or interview, just chatting, webinar or sales live, other)? Recorded,
live, or both? Which platforms (YouTube, Twitch, Kick, TikTok, Instagram, Facebook)? Horizontal,
vertical, or both?

**Round 2: the setup.** How many cameras and which (webcam, phone, mirrorless)? Which microphone? How
many monitors? For games: PC or console (capture card)? For react: where does the video play (browser
on a second monitor, a window)? Do they want the chat on screen, and what is the channel? Alerts
(StreamElements or Streamlabs widget URL)? Live texts they change often (lesson title, "now playing",
episode number)?

**Round 3: the client.** Who is it (person or company), what is the niche, who watches? Website and
social profiles to look at? Logo files? Brand guidelines? Creators or channels whose look they admire,
and looks they hate? How should it feel (three adjectives)?

Never ask for stream keys, passwords or account logins: the user pastes the stream key into OBS
themselves (see `references/obs-setup.md`).

## Phase 2: Study the client before designing anything

The scenes must look like this client and nobody else. Do not reuse fonts, colors or animations from
a previous client or from the examples out of habit. Follow `references/brand-study.md`:

1. Create the kit folder in a stable place the user chooses (e.g. `Documents/<Client> OBS`), never in
   a temp or downloads folder: OBS will point to these files by absolute path.
2. Collect evidence: `python scripts/inspect_brand.py <kit> --url <site> [--url <channel or about page>] [--logo <file>]`.
   It extracts the fonts and colors the brand really uses, finds social profiles, takes the palette of
   the logo and screenshots the site. **Open the screenshots and look at them.** Visit the social
   profiles and recent thumbnails too if you can browse.
3. If there is no brand yet (a new streamer), build one from the interview: niche conventions, the
   games or topics, the audience, the adjectives, the references they like.
4. Write `<kit>/research/brief.md` (template in the reference): who they are, audience, evidence found,
   personality, what to keep, what to avoid, and **two or three distinct design directions**, each with
   palette, type pairing, shapes, motif and motion idea, tied to the evidence.
5. Show the directions to the user in a few lines each and let them pick or mix. Don't go further
   until they choose.

## Phase 3: Scene plan

Translate the use into scenes with `references/scenes.md` (presets like `tutorial`, `gameplay`,
`react`, `just_chatting`, `side_by_side`, `starting`, `brb`, `ending`, or custom layouts). Present a
short table: scene name, what is on screen, when they would use it, hotkey. Add only scenes they will
really switch to; a live usually needs starting, main content, chatting and ending, while a recorded
course needs no waiting screens. Confirm before building.

## Phase 4: Theme and config

1. Write the client's theme in `<kit>/theme/theme.css` and `<kit>/theme/theme.js` following
   `references/theme.md`: it defines how frames, panels, texts, pills, badges, countdowns and the
   animated background look and move. The scene presets only decide where things go.
   The examples (`examples/zuuuw-academy`, `examples/novaplays`) show the contract and two opposite
   looks. You may start from one with `--theme-from` to save typing, but rewrite it for this client
   before showing anything.
2. Write `<kit>/studio.json` (`references/config.md`): language, mode, platform, brand, socials, colors
   and fonts from the chosen direction, sources, scenes, hotkeys, OBS and audio settings. Copy the logo
   into the kit. Fonts can be any Google Font (downloaded automatically) or the brand's own files.
3. Build: `python scripts/build_kit.py <kit>`. Fix every ERROR; read every WARN (contrast warnings
   matter: video compression eats thin, low-contrast text).

## Phase 5: Preview, critique, iterate

`python scripts/preview.py <kit> [--sample camera=photo.jpg --sample screen=app.png ...]` renders every
scene to `<kit>/preview/` and a contact sheet `all.png`. Ask the user for a photo of themselves and a
screenshot of their game or platform: real samples make the preview honest.

Look at every PNG yourself before showing it, as a picky art director: Does it look like this client
or like a template? Is text readable at 50% size (how most viewers see it on a phone)? Does anything
overlap the camera, the game HUD, the chat? Is the background calmer than the content? Fix, rebuild,
re-render. Then show the contact sheet to the user (path or image) and iterate on their feedback until
they approve. Changes go into `theme/` and `studio.json`, never into `overlays/` (rebuilt each time).

## Phase 6: Set up OBS

Follow `references/obs-setup.md`. In short:

1. OBS 30 or newer installed (`winget install --id OBSProject.OBSStudio -e`, `brew install --cask obs`,
   or the distro package). Tell the user before installing software. `python -m pip install obsws-python`.
2. With OBS closed: `python scripts/enable_websocket.py`. Then open OBS (and plug in camera and mic).
3. `python scripts/configure_obs.py <kit>`: profile, collection, canvas, fps, encoder, recording
   format, bitrate, mic with noise suppression/compressor/limiter, desktop audio on or off, every source
   and scene in the right order. `--dry-run` shows what it would do. It reads the websocket password
   from OBS's config, so never print or ask for it.
4. Close OBS, `python scripts/hotkeys.py <kit>`, reopen OBS.
5. Verify with the user: switch every scene, check camera framing and that the mic meter moves, record
   10 seconds and check the file (`ffprobe`), test each hotkey. What only the user can do: paste the
   stream key (Settings > Stream), pick the window for window captures, pick a camera the script could
   not match, log in to chat or alert widgets.

## Phase 7: Hand-off

The kit's `README.md` (generated) lists scenes, hotkeys and live texts. Show the user how to change a
live text: edit `<kit>/text/<key>.txt` or `python scripts/set_text.py <kit> title "New title"`; OBS shows
it within 2 seconds. Remind them: to change the look or the scenes, ask the AI to edit `studio.json` or
the theme and run `build_kit.py` and `configure_obs.py` again. If they also record the camera on a
separate device, a clap at the start gives the editor a sync point.

## Rules that save hours

- The kit folder must not move after OBS is configured; if it does, rebuild and reconfigure.
- `configure_obs.py` and `build_kit.py` are idempotent: re-run them instead of fixing OBS by hand.
- `hotkeys.py` and `enable_websocket.py` only work with OBS closed (OBS overwrites its files on exit).
- Do not delete scenes the user made outside the kit; `--prune` exists only for when they ask.
- Keep motion behind content: a moving background is fine on waiting screens, but around a game or a
  screen being taught it must be slow, small and low-contrast. Browser sources cost GPU; prefer CSS
  animations and transforms over heavy canvas or video loops.
- Never put secrets (stream keys, passwords, tokens) in `studio.json`, the kit or the chat.
