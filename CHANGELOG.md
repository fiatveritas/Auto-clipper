# Changelog

All notable changes to Auto-Clipper.

## [Unreleased]

### Added
- **Bundled YOLO weights** (`models/best.pt`, ~21 MB) — fine-tuned YOLOv11n on the Arc Raiders v0.11 Roboflow dataset. Detects 13 entity classes (raider, bombardier, leaper, turret, fireball, pop, probe, hornet, wasp, snitch, rocketeer, bastion, raider-down). YOLO detection mode works out of the box — no more "requires a .pt".
- **Curl-pipe installer** (`install-remote.sh`) — Homebrew-style one-line install that bypasses macOS Gatekeeper entirely by pulling the repo via `curl` in Terminal (curl-downloaded files never get the quarantine flag). Re-running does a clean reinstall, preserving VODs/clips/library/weights.
- **`/api/health` endpoint** — returns ffmpeg availability, YOLO weights status, yt-dlp version, and Python version. Useful for debugging "nothing works".
- **Startup banner** — `python app.py` now prints the URL + environment details (Python, ffmpeg path, YOLO weights size, yt-dlp version) before starting.
- **`ClipMode` enum** (`analysis/clip_modes.py`) — CV / YOLO / VOICE / HYBRID / ALL with clean property gates (`uses_cv`, `uses_yolo`, `uses_voice`, `is_live`).
- **`reinstall.sh` / `reinstall.bat`** — idempotent clean reinstall that preserves VODs, clips, library, sessions, uploads, weights, and config.
- **Landing page** at <https://auto-clipper.pages.dev/> with install guide, FAQ, bundled weights docs, and Gatekeeper workaround.

### Changed
- **VOD download speedup: ~4× faster.** `concurrent_fragment_downloads=16` + `http_chunk_size=10 MB` + `retries=5` + `fragment_retries=5` + application-level exponential backoff. A 1-hour Twitch VOD now downloads in ~2 min on a 300 Mbps link instead of ~8 min.
- **NaN-safe fps fallback** across all 7 analyzer modules (`motion_detector`, `scene_detector`, `detector`, `hybrid_detector`, `ai_analyzer`, `yolo_local_analyzer`, `roboflow_model_analyzer`). The old `cap.get(CAP_PROP_FPS) or 30.0` idiom missed NaN (NaN is truthy in Python). Now uses the `fps != fps` identity check.
- **`YOLODetector.detect()` accepts numpy ndarrays directly** — skips the per-frame temp-JPEG disk round-trip. Shaves ~100 ms per sampled frame on a 1-hour VOD.
- **`cap.grab()` for non-sampled frames** in the CV loop — skips `cvtColor` + numpy copy on frames we'd throw away. 28.6× realtime on pixel-only smoke test.
- **Device autodetect** in `YOLODetector.__init__` — picks CUDA > MPS (Apple Silicon) > CPU automatically when no device is pinned.
- **Smarter YOLO/pixel blend** in `ScoringEngine.combine()` — strong pixel signals (≥60) get an 80% floor so clearly-combat frames don't get buried when YOLO misses.
- **Detection method dropdown** regrouped into optgroups ("Works out of the box" / "Advanced" / "Needs API key / weights"). Default flipped to `arc_cv_pipeline` (Auto-Clipper's own CV pipeline, no external deps).
- **Graceful fallback** when `yolo_local` mode can't find/load weights — falls through to CV pipeline instead of erroring out.
- **`run.sh` + `run.bat` + `Auto-Clipper.command` + `Auto-Clipper.bat`** — all now run `pip install --upgrade yt-dlp` on every launch and warn if ffmpeg is missing. Catches the #1 and #2 "nothing works" root causes before the user even sees the UI.
- **App theme** — aligned with the landing page: Twitch purple (`#9147ff`) primary, hot pink CTA (`#ff3e7f`), mint accent (`#00e6c3`), OLED black background. Russo One display font, Chakra Petch UI labels, JetBrains Mono code.
- **Full UI overhaul** of the Flask web app — sidebar → floating glass pill, cards → bento-style gradient surfaces with hover glow, buttons → accent→CTA gradient, inputs → glass + purple focus ring, progress bar → gradient with shimmer sweep, clip cards → mint live-dot + mono timestamps, empty states → animated radial glow.
- **Consolidated Arc Raiders profile** — removed 6 variant profiles (v2 Refined, v3 Aggressive, v4 Audio-Heavy, v5 Motion-Based, v6 Precision, v7 PvPvE, 780 lines). One "Arc Raiders" profile in the game selector.
- **`--depth=1` clones** in `install-remote.sh` and `reinstall.sh` — saves ~50-80 MB on fresh installs given the repo now ships a 21 MB `.pt` file plus history.
- **Windows install command** (`git clone ... || git -C Auto-clipper pull && cd ... && install.bat && run.bat`) is now idempotent — re-running pulls latest instead of erroring out on "destination path already exists".

### Fixed
- **VOD download failures** — root cause was stale `yt-dlp` + short `socket_timeout=30` + no fragment retries. Twitch HLS fragments occasionally take >30s on CDN hiccups; one hiccup killed the entire download. Fixed by raising timeout to 120s, adding `retries=5` + `fragment_retries=5` + a 3-attempt application-level retry loop with exponential backoff, and auto-upgrading `yt-dlp` on every launch.
- **Theme toggle null-deref** — `getElementById("theme-toggle")` returned `null` after the UI overhaul switched to class-based buttons, silently breaking the light/dark toggle. Now guarded with `?.` equivalent.
- **HUD digit class contamination** — v0.11 Roboflow dataset has classes 0, 1, 5 labelled as literal digit strings ("0", "1", "5"); they were getting `base=5` score each. Zeroed them out so they no longer inflate highlight scores.
- **Stale README references** to nonexistent `games/` directory — profiles live in `analysis/game_profiles.py`.
- **Site README link** was `/blob/main/README.md` which 404s when default branch isn't `main`. Now uses `#readme` which resolves to whatever the current default branch is.

### Infrastructure
- Cloudflare Pages deployment via Wrangler CLI — landing site auto-deploys from `site/` on every push.
- Monitor-driven weight auto-commits during YOLO training — each epoch's improved weights auto-commit + push without manual intervention.

---

*Generated during the marathon debugging + improvement loop on 2026-04-18.*
