## What's new

### 🎤 Clip It — voice-triggered clipping
Say **"clip it"**, **"clip that"**, **"clip this"**, **"save that"**, or **"save clip"** and the last 30 seconds drops into your library, ready to trim/extend in the editor. Powered by `faster-whisper` with graceful fallback to `openai-whisper`.

Pick your clipping mode from the Detection Settings panel:
- **CV** — pixel analysis only (muzzle flash, damage vignette, audio peaks, HUD zones). Fastest. No weights needed.
- **YOLO** — neural object detection (raiders, bosses, turrets, 13+ classes per game). Most precise. GPU recommended.
- **Clip It** — voice trigger only. Live-stream-friendly workflow.
- **Hybrid** — every signal firing in parallel. Best recall, no missed moments.

### ⚡ Computer-vision pipeline rewrite
Three compounding perf wins in [`analysis/arc_clip_detector.py`](analysis/arc_clip_detector.py):

- **Killed the per-frame temp-JPEG round-trip.** `YOLODetector.detect()` now accepts numpy ndarrays directly. Ultralytics handles BGR natively — there's no reason to write every sampled frame to `/tmp` just to read it back.
- **Fast-skip non-sampled frames with `cap.grab()`.** Maintains decoder state but skips the `cvtColor` + numpy copy we'd throw away. **28.6× realtime** on the pixel-only smoke test.
- **Device autodetect.** YOLO now picks CUDA > MPS (Apple Silicon) > CPU automatically.

Plus:
- NaN-safe fps fallback (the old `or 30.0` didn't catch NaN — which is truthy)
- Smarter `combine()`: strong pixel signals (≥60) get an 80% floor so a clear muzzle-flash frame doesn't get buried when YOLO misses it
- Zeroed out the v0.11 dataset's 0/1/5 HUD-digit class artifacts

### 🌐 New landing page — auto-clipper.pages.dev
Full static site deploying to Cloudflare Pages. No build step, no framework — just HTML + CSS + vanilla JS.

- Hero with **real Arc Raiders gameplay** + 3 YOLO bounding boxes pulled straight from the training label polygons (frame 0626 from the v0.11 Roboflow export)
- **DMG-easy install section**: OS autodetection + one-line copy-paste per platform (Mac / Windows / Linux)
- **Clip It** section with animated mic, pulsing rings, live-listening transcript, and the 4-way mode picker
- Features bento grid, how-it-works, supported games, FAQ, trust row
- Cache-control hardened so updates actually reach visitors instead of being wedged on immutable

### 🏗️ Architecture
- New [`analysis/clip_modes.py`](analysis/clip_modes.py) — `ClipMode` enum orchestrating CV / YOLO / Voice paths
- `ArcClipDetectorAdapter` takes a `clip_mode` kwarg and gates detectors. YOLO-only mode skips pixel analysis for ~30% wall-time savings.
- Voice triggers delegate to the existing [`analysis/clip_trigger_detector.py`](analysis/clip_trigger_detector.py) (Whisper-based) — the UI surface just makes it discoverable.

## Install
```bash
# macOS / Linux
git clone https://github.com/bendawg2010/Auto-clipper.git && cd Auto-clipper && ./install.sh && ./run.sh

# Windows (Command Prompt)
git clone https://github.com/bendawg2010/Auto-clipper.git && cd Auto-clipper && install.bat && run.bat
```

Full install guide → <https://auto-clipper.pages.dev/#install>

## Supported games
- **Arc Raiders** — YOLO v0.11, 13+ entity classes (raider, raider-down, rocketeer, bastion, leaper, bombardier, hornet, wasp, snitch, pop, fireball, tick, turret, probe, queen, sentinel)
- **War Thunder** — pixel-only profile

Adding a game = dropping a profile in `games/`. The engine stays the same.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
