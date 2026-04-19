# Auto-Clipper v0.12.0

## Install — one command, no Gatekeeper dialogs

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/bendawg2010/Auto-clipper/main/install-remote.sh)"
```

Same pattern Homebrew uses. Files fetched via `curl` in Terminal skip the macOS quarantine flag, so there's no "cannot verify" dialog — ever. Works on Mac + Linux. Re-running does a clean reinstall (preserves your VODs, clips, library, weights).

**Windows (Command Prompt):**
```cmd
git clone https://github.com/bendawg2010/Auto-clipper.git 2>nul || git -C Auto-clipper pull && cd Auto-clipper && install.bat && run.bat
```

Full install guide → <https://auto-clipper.pages.dev/>

## What's in this release

### 🎯 Bundled YOLO weights
`models/best.pt` (~5 MB, stripped-optimizer checkpoint) ships with the repo. YOLOv11n fine-tuned on the Arc Raiders v0.11 Roboflow dataset (2880 training frames). Detects 13 entity classes: raider, raider-down, rocketeer, bastion, leaper, bombardier, hornet, wasp, snitch, pop, fireball, probe, turret. **YOLO detection mode works the moment you install** — no API keys, no manual weight download.

### 🎤 Clip It — voice-triggered clipping
Say **"clip it"** / **"clip that"** / **"clip this"** / **"save that"** / **"save clip"** and the preceding 30 seconds drops into your library, ready to trim/extend in the editor. Powered by `faster-whisper` with graceful fallback to `openai-whisper`.

Pick your clipping mode:
- **CV** — pixel analysis only. Fastest, no weights needed.
- **YOLO** — neural object detection. Runs on the bundled weights.
- **Clip It** — voice trigger only. Live-stream-friendly.
- **Hybrid** — every signal firing in parallel. Best recall.

### ⚡ Computer-vision pipeline rewrite
- **Killed the per-frame temp-JPEG round-trip** — `YOLODetector.detect()` accepts numpy ndarrays directly
- **Fast-skip non-sampled frames with `cap.grab()`** — 28.6× realtime on pixel-only smoke test
- **Device autodetect** — CUDA > MPS (Apple Silicon) > CPU
- **NaN-safe fps fallback** across 8 detectors via shared `analysis/video_utils.py`
- **Smarter combine()** — strong pixel signals (≥60) get an 80% floor so clearly-combat frames don't get buried when YOLO misses
- **VOD downloads 4× faster** — 16-way concurrent HLS fragment downloads (1-hour Twitch VOD now downloads in ~2 min on 300 Mbps vs ~8 min before)

### 🌐 Landing page
Live at <https://auto-clipper.pages.dev>. Hero demo uses real Arc Raiders gameplay + YOLO bounding boxes pulled from the training labels. Full install guide, FAQ, and Gatekeeper workaround.

### 🏗️ Infrastructure
- **`/api/health`** endpoint + startup banner — both read from a shared `_ENV_INFO` snapshot so they can't drift
- **Preflight checks** on `run.sh`, `run.bat`, `Auto-Clipper.command`, `Auto-Clipper.bat` — ffmpeg availability + yt-dlp auto-upgrade (weekly-gated, backgrounded)
- **Friendly download errors** — raw yt-dlp messages translated into actionable user text
- **`reinstall.sh` / `reinstall.bat`** — clean reinstall that preserves VODs, clips, library, sessions
- **Makefile** with `make install/run/test/lint/clean/deploy-site`
- **16 smoke tests** (`tests/test_smoke.py`) — ClipMode enum, scoring safety floor, HUD digit zero-check, YOLO class roundtrip, URL validator, friendly-error mapping, shell-script syntax, bundled-weights size, and more

## Supported games
- **Arc Raiders** — YOLO v0.11, 13 entity classes
- **War Thunder** — pixel-only profile
- 43 total game profiles in `analysis/game_profiles.py` — adding a new game = one dict entry

## What was removed
- 5 duplicate game profile definitions (-464 lines of dead code)
- 555 lines of orphan CSS
- 6 unused imports across analysis modules
- 1 tautological test (now calls the real matcher)

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
