# Contributing to Auto-Clipper

Thanks for the interest! Auto-Clipper is a small, opinionated Python/Flask app — contributions are welcome, and the scope is intentionally narrow: find highlights in gameplay VODs, locally, without cloud dependencies.

## Dev loop

```bash
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
./install.sh   # or install.bat on Windows
./run.sh       # app at http://localhost:8080
```

Run the smoke tests before opening a PR:

```bash
python tests/test_smoke.py
# or: python -m pytest tests/
```

Smoke tests cover the import chain + core API contracts and run in ~2 seconds.

## Project layout

```
app.py                        # Flask app + job orchestration
clip_manager.py               # VOD download + clip extraction via yt-dlp + ffmpeg
analysis/
  arc_clip_detector.py        # Main CV pipeline (YOLO + pixel analysis fusion)
  game_profiles.py            # Per-game colour/region detection profiles
  clip_modes.py               # CV / YOLO / VOICE / HYBRID / ALL enum
  clip_trigger_detector.py    # "clip that!" voice trigger via Whisper
  audio_detector.py           # Audio-spike-only detection
  motion_detector.py          # Frame-diff motion detection
  scene_detector.py           # Scene change detection
  hybrid_detector.py          # Audio + motion + scene combined
  ai_analyzer.py              # xAI Grok Vision analyzer (needs API key)
  roboflow_*.py               # Roboflow-hosted model analyzers (need API key)
  yolo_local_analyzer.py      # Local YOLO .pt inference
templates/index.html          # Single-page Flask template
static/
  css/style.css               # App theme
  js/app.js                   # All frontend JS
models/best.pt                # Bundled Arc Raiders YOLO weights
site/                         # Landing page (deploys to Cloudflare Pages)
tests/test_smoke.py           # Fast regression tests
install.sh / install.bat      # One-click installers
run.sh / run.bat              # Launchers
Auto-Clipper.command / .bat   # Double-click launchers for non-techies
install-remote.sh             # Curl-pipe installer (bypasses macOS Gatekeeper)
reinstall.sh / reinstall.bat  # Clean reinstall that preserves user data
```

## Adding a new game

1. Open `analysis/game_profiles.py`
2. Copy the `arc_raiders` block as a template
3. Tune the HSV color ranges + regions + thresholds for your game
4. Test with a short VOD in the app
5. Open a PR

Each profile defines:
- **Colour ranges** (HSV) for things like kill-feed text, damage vignette, muzzle flash
- **Screen regions** (normalized 0-1 bbox) telling the engine where each signal lives
- **Detection weights** + multipliers
- **AI prompt text** for xAI Grok Vision analysis

## Pull request checklist

- [ ] Smoke tests pass (`python tests/test_smoke.py`)
- [ ] Touched shell scripts still parse (`bash -n <script>`)
- [ ] Python syntax clean (`python3 -c "import ast; ast.parse(open('file').read())"`)
- [ ] No hardcoded absolute paths
- [ ] New user-facing error messages suggest a fix
- [ ] README / CHANGELOG updated if behaviour changes

## Bugs

File an issue at <https://github.com/bendawg2010/Auto-clipper/issues> with:

- What you did
- What you expected
- What happened
- Output of `GET http://localhost:8080/api/health` (the endpoint returns ffmpeg + weights + yt-dlp versions for quick debugging)
- Relevant lines from the terminal where you ran `./run.sh`

Debug tip: `yt-dlp --skip-download -F <your-vod-url>` tells you quickly whether the URL is fetchable at all — 99% of "my download doesn't work" reports turn out to be a deleted / private / geo-blocked VOD.

## License

By submitting a PR you agree to release your contribution under the [MIT License](LICENSE) that governs this repo.
