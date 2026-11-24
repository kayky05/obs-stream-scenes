# Setting up OBS

## 1. Install

| OS | Command |
| -- | ------- |
| Windows | `winget install --id OBSProject.OBSStudio -e` |
| macOS | `brew install --cask obs` |
| Linux | distro package or `flatpak install flathub com.obsproject.Studio` |

OBS 30 or newer (WebSocket 5 is built in since 28). Open it once so it creates its config folder,
dismiss the auto-configuration wizard, close it. Python: `python -m pip install obsws-python pillow`.

Windows is the most tested path. macOS and Linux work with the same scripts (they pick the right
capture types), but game capture exists only on Windows and screen capture on macOS asks for the
Screen Recording permission the first time.

## 2. WebSocket

With OBS closed: `python scripts/enable_websocket.py`. It enables the server on port 4455 with a
password stored in OBS's config, and `configure_obs.py` reads it from there. Use `--show-password`
only to pair a phone remote (OBS Blade, Touch Portal) and tell the user to keep it private.

## 3. Configure

Open OBS, plug in the camera and microphone, then:

```
python scripts/configure_obs.py <kit>            # --dry-run to see the plan first
```

It creates or updates the profile and scene collection named after the client, sets the canvas, fps,
encoder, recording format and folder, bitrate for streaming, the microphone with noise suppression
(RNNoise), compressor 4:1 at -18 dB and limiter at -3 dB, desktop audio on or off, every source and
every scene in layer order. Run it again whenever the kit changes. If a camera reported no size yet,
run it once more after the camera shows image so the crop is exact.

## 4. Hotkeys

Close OBS, `python scripts/hotkeys.py <kit>`, reopen. Scene hotkeys plus record and stream toggles.
They are global: they work while the game or the browser has focus.

## 5. Verify with the user

- Every scene: switch with the hotkeys, look for black boxes or misaligned frames.
- Camera fills its frame without black bars; face not cut by a frame edge.
- Speak: the mic meter moves in the yellow-green range and never hits red.
- Desktop audio: present in gameplay/react, absent in recorded lessons if set so.
- Record 10 seconds and inspect: `ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate <file>`.
- Live texts: change one with `set_text.py` and watch OBS update in about 2 seconds.

## What only the user does

- **Stream key**: Settings > Stream > choose the service > "Connect account" or paste the key. Never
  ask for it, never write it anywhere.
- Pick the window for window-capture sources (Properties > Window).
- Choose the camera or mic if the name hints matched nothing.
- Log in or configure chat and alert widgets on the provider's site.

## Chat and alerts URLs

| Platform | Chat URL for a browser source |
| -------- | ----------------------------- |
| Twitch | `https://www.twitch.tv/popout/<channel>/chat?popout=` (or a StreamElements/Streamlabs chat widget for a transparent style) |
| YouTube | `https://www.youtube.com/live_chat?is_popout=1&v=<VIDEO_ID>` changes every live; a StreamElements/Streamlabs/Restream chat widget URL stays fixed |
| Kick | `https://kick.com/popout/<channel>/chat` |
| Multi-platform | Restream or Social Stream Ninja chat overlay URL |

Alerts: the "Alert Box" widget URL from StreamElements or Streamlabs, added as the `alerts` source.
Widget URLs contain a private token: they go in `studio.json` of the user's own machine only; never
publish a kit with them.

## Equipment notes

**Cameras** (all become the same "Camera" source; switching devices keeps position and crop):

| Camera | How |
| ------ | --- |
| USB webcam | Plug in. |
| iPhone / Android | Camo, Iriun or (macOS) Continuity Camera. USB cable is steadier than Wi-Fi. Use it for image only; audio comes from the mic. |
| Sony with "USB Streaming" (ZV-E10 II, a6700, FX30, a7 IV...) | Enable USB Streaming in the camera menu, connect USB-C. Up to 1080p. |
| Any camera with clean HDMI | HDMI to a capture card (Elgato Cam Link or similar); turn off on-screen info on the HDMI output. Dummy battery for long sessions. |

**Microphones**: wireless receivers (Hollyland Lark, DJI Mic, Rode Wireless) and USB mics show up by
name; the hints in `devices.mic` pick them. One receiver per transmitter at a time.

**Consoles**: capture card between console and TV (passthrough), card's USB to the PC; source type
`capture_card`, hints in `devices.console`. Turn off HDCP on PlayStation (Settings > System).

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| Screen capture is black | Laptops with two GPUs: in the source properties choose the "Windows 10 (1903+)" capture method. |
| Camera black or "device in use" | Another app holds it (Teams, Meet, Camo in another app). Close it, then Deactivate/Activate the source. |
| Fonts look generic in a scene | The kit folder moved or fonts failed to download: run build_kit.py again and check its warnings. |
| Overlay frame and capture misaligned | Kit rebuilt with a new layout but OBS not reconfigured: run configure_obs.py. |
| Background blank | OBS cannot find the overlay file (folder moved): rebuild and reconfigure. |
| Hotkeys do nothing | hotkeys.py ran with OBS open; close OBS and run it again. |
| Countdown does not restart | The starting scene's layer restarts when the scene becomes active; switch away and back. |
| Voice low or clipping | Set gain on the mic/receiver itself; aim for speech peaks in the yellow. The limiter stops clipping, it does not fix a low voice. |
| Dropped frames while live | Lower video_bitrate, use the GPU encoder, close heavy browser tabs; check Stats in OBS. |
