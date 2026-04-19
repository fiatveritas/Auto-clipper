# Auto-Clipper v0.13.0

**77 commits since v0.12.0.** Polish release focused on robustness, dead-code removal, and test coverage. Everything in v0.12.0 still works — this version just has fewer sharp edges.

## Install

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/bendawg2010/Auto-clipper/main/install-remote.sh)"
```

Re-running does a clean reinstall that preserves your VODs, clips, library, sessions, and weights. Windows users: `git clone https://github.com/bendawg2010/Auto-clipper.git 2>nul || git -C Auto-clipper pull && cd Auto-clipper && install.bat && run.bat`.

Full install guide → <https://auto-clipper.pages.dev/#install>

## What's new vs. v0.12.0

### 🧹 Robustness
- **Bulk null-safety** on 23 POST endpoints — malformed JSON bodies now return a clean 400 instead of AttributeError 500s
- **URL validation hardened** — rejects live-channel URLs (`twitch.tv/username`), accepts 6 more legitimate VOD patterns (mobile Twitch, YouTube Shorts, live-stream replays)
- **Friendly download errors** — raw yt-dlp messages translated into actionable text: "VOD not found", "VOD is geo-blocked", "FFmpeg isn't installed", etc.
- **ffprobe + thumbnail ffmpeg calls guarded** — missing binary mid-pipeline no longer crashes the request
- **`_collect_env_info()`** — `/api/health` + startup banner share one snapshot so they can't drift
- **yt-dlp auto-upgrade gated to weekly** — first version blocked every launch on a pip round-trip (1-15 s); now backgrounded + timestamped

### 🏗️ Architecture
- **`analysis/video_utils.py`** — new shared `safe_fps()`, `probe_video()`, `frame_interval_for()` helpers. Kills 8 copies of the NaN-safe fps guard that were drifting apart (two used `math.isnan`, six used `fps != fps`, one missed NaN entirely with `or 30.0`)
- **`_FRIENDLY_DOWNLOAD_ERRORS` lookup table** — yt-dlp error → user message mapping is now one tuple per pattern instead of a 5-arm if/elif chain

### 🧪 Testing
- **16 regression tests** in `tests/test_smoke.py` (up from zero) — ClipMode enum, scoring safety floor, HUD digit zero-check, YOLO class roundtrip, URL validator, friendly-error mapping, `_ENV_INFO` shape, shell-script syntax, bundled-weights size, time parser, and more
- **`tests/conftest.py` + `__init__.py`** — `python -m pytest tests/` works out of the box
- **Tautological test fixed** — `test_match_trigger_phrases` now calls the real `_find_triggers` instead of reimplementing the regex

### 🧼 Dead code removal
- **-464 lines** from `analysis/game_profiles.py` — 5 duplicate game profile definitions (destiny_2, helldivers_2, dota_2, diablo_4, street_fighter_6) were each defined twice; the second silently overwrote the first
- **-555 lines** from `site/styles.css` — two rounds of orphan CSS cleanup (old `.install`, `.install2`, `.dl-alt`, `.install2__reinstall` blocks from the simplified install section)
- **-~10 unused imports** across analysis/ (numpy, os, base64, glob, send_file, sys, etc.)
- **Dead expression** in `roboflow_analyzer.py` — `cls_preds.get(...)` call with no assignment (actual bug)
- **Unused `global watch_folder_running`** in app.py — variable is only read, no `global` needed

### 📚 Docs + DX
- **`CHANGELOG.md`** documenting all changes
- **`CONTRIBUTING.md`** with dev loop + project layout + PR checklist
- **`LICENSE`** — MIT, explicit
- **`Makefile`** with `make install/run/reinstall/test/lint/clean/deploy-site` — auto-detects Python (venv → python3 → python)
- **Favicon + theme-color** in the Flask app template (matches the landing page's Twitch purple)
- **Desktop launcher** title updated: "Arc Raiders Auto-Clipper" → "Auto-Clipper" (we support multiple games now)
- **README + release notes** corrected — bundled weights size is ~5 MB stripped-optimizer, not 21 MB

### 🌐 Landing site
- **OG / Twitter social card images** added (hero screenshot shows on Discord / Twitter / Slack unfurls)
- **`theme-color` meta** — mobile browser chrome matches the Twitch purple brand
- **CSS now 1595 lines** (was 2150 at peak) — same visual fidelity, half the code

## Health-check

After installing, `curl http://localhost:8080/api/health` returns:

```json
{
  "status": "ok",
  "python_version": "3.11.x",
  "platform": "Darwin",
  "ffmpeg": {"available": true, "path": "/opt/homebrew/bin/ffmpeg"},
  "yolo_weights": {"path": "models/best.pt", "size_mb": 5.4},
  "yt_dlp_version": "2026.03.17"
}
```

Same data is shown in the startup banner when you run `python app.py`.

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
