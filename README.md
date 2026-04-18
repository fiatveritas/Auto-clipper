# Auto-Clipper

**Auto-find the best moments in your Twitch or YouTube VODs** — kills, combat, explosions, and more. Paste a link or upload a file, get highlight clips. Free, open-source, runs 100% on your machine.

🌐 **[auto-clipper.pages.dev](https://auto-clipper.pages.dev)** — landing page + one-line install guide
⭐ **[github.com/bendawg2010/Auto-clipper](https://github.com/bendawg2010/Auto-clipper)** — source
🎮 **Supports:** Arc Raiders (YOLO, 13+ entity classes), War Thunder (pixel analysis). More games: just drop in a profile.

---

## What's New

- 🎤 **Clip It** — say *"clip it"*, *"clip that"*, *"clip this"*, *"save that"*, or *"save clip"* and the last 30 seconds gets saved as a clip. Then you can trim, extend, or re-cut it in the editor.
- 🧠 **Clipping mode selector** — pick **CV** (pixel analysis, no weights needed), **YOLO** (neural object detection), **Clip It** (voice triggers), or **Hybrid** (everything on at once).
- ⚡ **CV pipeline rewrite** — numpy-direct YOLO inference, `cap.grab()` frame-skip, device autodetect (CUDA / MPS / CPU), safer fps handling. ~28× realtime on the smoke test in pixel-only mode.
- 🛠️ **Manual clip** — click any library VOD + enter a timestamp to instantly extract the previous 30s.

---

## One-Command Install

### macOS / Linux
```bash
git clone https://github.com/bendawg2010/Auto-clipper.git && cd Auto-clipper && ./install.sh && ./run.sh
```

### Windows (Command Prompt)
```cmd
git clone https://github.com/bendawg2010/Auto-clipper.git && cd Auto-clipper && install.bat && run.bat
```

First run installs Homebrew / Python / FFmpeg automatically. Every run after is just `./run.sh` (or `run.bat`). Your browser opens at **http://localhost:8080**.

> **Mac security note:** If macOS blocks the file, open Terminal and run
> `xattr -d com.apple.quarantine ~/Downloads/Auto-clipper-*/Auto-Clipper.command`
> Only needed once.

Don't like command lines? Use the ZIP fallback:
1. Green **"<> Code"** button → **"Download ZIP"**
2. Unzip it, open the folder
3. Double-click **`Auto-Clipper.bat`** (Windows) or **`Auto-Clipper.command`** (Mac)

---

## How to Use

Once the app is running in your browser:

### 1. Pick your game
Top of the page — **Arc Raiders** or **War Thunder**. Each game has its own detection profile (different kill feeds, UI zones, colors). The selection is remembered next session.

### 2. Pick your clipping mode

| Mode | What it does | When to use |
|------|-------------|-------------|
| **CV** | Pixel analysis only — muzzle flash, damage vignette, audio peaks, HUD zones | Fastest, works on any machine, no model weights required |
| **YOLO** | Neural object detection (raiders, turrets, bosses, 13+ classes) | Most precise. Needs `.pt` weights + GPU recommended |
| **Clip It** | Voice-triggered only — scans audio for *"clip it"* / *"clip that"* | Streamers who want a shout-it-and-save workflow |
| **Hybrid** | CV + YOLO + voice triggers firing in parallel | Best recall, widest net, no missed moments |

Mode selection is per-session and lives in the Detection Settings panel.

### 3. Give it a VOD
Either:
- **Paste a Twitch / YouTube URL** (optionally limit to a start/end time to save download time)
- **Upload a local file** from your computer
- **Drop files into the library** and scan existing VODs on demand

### 4. Wait for analysis
1. VOD downloads (progress bar shows %)
2. Pipeline samples frames and runs the selected mode(s)
3. Clips get extracted + clustered

A 1-hour VOD runs in ~3-5 minutes on pixel-only mode. YOLO mode depends on your GPU.

### 5. Review & edit
Each highlight has:
- Thumbnail, label, timestamp, confidence bar
- **Trim** — ±1s / ±5s buttons, then **Re-cut Clip**
- **Download** — raw MP4
- **Make TikTok** — convert to 9:16 vertical

### 6. "Clip It" voice mode
With mode set to **Clip It** or **Hybrid**, the app scans the VOD's audio track via Whisper (`faster-whisper` preferred, `openai-whisper` fallback) and tags every occurrence of the trigger phrases. Each trigger creates a clip covering the **preceding 30 seconds** — the actual moment of action, not the reaction.

Default triggers: `clip it`, `clip that`, `clip this`, `save that`, `save clip`. Edit the list in the Detection Settings panel.

### 7. Manual clip (any timestamp)
In the library view, click **Clip** on any VOD and enter a timestamp — Auto-Clipper extracts the 30 seconds ending at that moment. Also available mid-session via the **Manual Clip** button in the clips toolbar.

---

## TikTok / Vertical Video

Click **Make TikTok** on any clip:

1. Pick a **preset layout** — "Cam: Top-Right" puts gameplay on top (70%), webcam on bottom (30%)
2. No webcam? Click **No Webcam** for full-screen gameplay
3. Custom layouts: drag on the frame to draw your own gameplay / webcam regions
4. Preview on the right
5. Click **Export TikTok Video** — processes and auto-downloads the vertical MP4

---

## iPhone / iPad Access

The app runs on your computer; view it from your phone:

1. Get Auto-Clipper running on your computer first
2. Find your computer's IP:
   - Mac: `ipconfig getifaddr en0` in Terminal
   - Windows: `ipconfig` → look for "IPv4 Address"
   - Usually something like `192.168.1.42`
3. On your iPhone (same Wi-Fi), open Safari → `http://YOUR_IP:8080`
4. Optional: Share → "Add to Home Screen" for an app icon

---

## Supported Games

| Game | YOLO classes | Pixel signals |
|------|-------------|--------------|
| **Arc Raiders** | `raider`, `raider-down`, `rocketeer`, `bastion`, `leaper`, `bombardier`, `hornet`, `wasp`, `snitch`, `pop`, `fireball`, `tick`, `turret`, `probe`, `queen`, `sentinel` | Red damage vignette, muzzle flash, blue Arc enemy glow, HUD zones, kill-feed colors, audio peaks |
| **War Thunder** | (pixel-only profile) | "Target Destroyed" banner, critical-hit flash, bomb/rocket hit colors, vehicle fires, explosions, damage vignette |

Adding a new game = dropping a new profile into `games/`. The detection engine is the same.

---

## AI Mode (optional)

By default Auto-Clipper uses pure computer vision (pixel + YOLO). No accounts, no API keys.

For smarter semantic analysis:

1. Click **"+ AI Mode (xAI Grok Vision)"**
2. Get a free API key at [x.ai](https://x.ai/)
3. Paste your key into the field

The AI knows the difference between "walking around doing nothing" and "intense firefight with a kill" — CV only sees colors and motion. AI mode finds better clips but uses API credits. Your key is stored locally only.

---

## YOLO Weights

**Bundled out of the box:** `models/best.pt` ships with the repo — a 5.4 MB YOLOv11n COCO-pretrained model. That means YOLO mode loads + runs the moment you install. It detects generic objects (person / car / etc.) rather than Arc Raiders entities, but the pixel + audio pipeline still catches real highlights on top of it.

**Upgrade to a real Arc Raiders model:**
1. Get the dataset → [Roboflow Universe — Arc Raiders Object Detection v13](https://universe.roboflow.com/valorantai/arc-raiders-8tjh4/model/11)
2. Train with ultralytics:
   ```bash
   yolo detect train model=yolo11n.pt data=path/to/arc-raiders/data.yaml \
       epochs=50 imgsz=640 device=mps  # or cuda / cpu
   ```
3. Overwrite `models/best.pt` with your `runs/detect/train/weights/best.pt`

The detector also auto-discovers `.pt` files in `weights/`, the repo root, and `runs/detect/train/weights/` — drop them wherever is convenient.

---

## Under the Hood

- **Python** (Flask web app, no frontend framework — vanilla JS)
- **OpenCV** for pixel analysis + video I/O
- **Ultralytics YOLO** (v11) for neural detection
- **FFmpeg** for VOD downloads + clip extraction + TikTok conversion
- **faster-whisper** / **openai-whisper** for voice trigger transcription
- **yt-dlp** for Twitch / YouTube downloads

The `analysis/` module is the core:
- `arc_clip_detector.py` — main orchestrator, CV + YOLO fusion
- `clip_modes.py` — `ClipMode` enum (CV / YOLO / VOICE / HYBRID / ALL)
- `clip_trigger_detector.py` — voice trigger / Whisper-based scanner
- Per-game profiles in `games/`

---

## Troubleshooting

**"python is not recognized" (Windows)**
You didn't check "Add python.exe to PATH" during installation. Uninstall Python, reinstall, and **check the box** on the very first installer screen.

**"git is not recognized" (Windows)**
Close + reopen Command Prompt. Still broken? Reinstall from [git-scm.com](https://git-scm.com/download/win).

**"ffmpeg is not recognized"**
Re-run `install.bat` (Windows) or `./install.sh` (Mac). It installs FFmpeg automatically.

**"brew: command not found" (Mac)**
Re-run `./install.sh`. It installs Homebrew automatically.

**Installer says it worked but `run.bat` does nothing**
Open Command Prompt manually:
```cmd
cd Auto-clipper
venv\Scripts\activate
python app.py
```
You'll see the actual error.

**Clips won't download from Twitch**
Make sure the VOD is **public**. Some streamers delete VODs after a few days, and subscriber-only VODs can't be downloaded without auth.

**iPhone can't connect**
- Same Wi-Fi network on both devices?
- Is Auto-Clipper actually running? (`run.bat` / `run.sh` must stay open)
- Try turning off VPN on both devices
- Windows firewall may block port 8080 — try temporarily disabling it

**Port 8080 already in use**
Something else has it. Close other apps, or edit `app.py` and change `port=8080` to `port=8081` (then use `http://localhost:8081`).

**Analysis found boring clips**
Switch to **Hybrid** mode for best recall, or drop `best.pt` in the repo root to enable YOLO. AI mode finds the best clips but costs API credits.

**Analysis takes forever**
Use **"Download specific part"** to analyze just a portion of a long VOD. A 30-minute section runs way faster than a 5-hour stream. For YOLO on CPU, sample at a lower FPS or switch to CV-only mode.

**"no microphone" on Clip It mode**
Voice triggers currently scan the VOD's **audio track** (post-recording). True live mic listening is on the roadmap — use OBS to record your mic into the stream for now.

---

## Contributing

PRs welcome. New game profile = new file in `games/`. Bug reports: [GitHub Issues](https://github.com/bendawg2010/Auto-clipper/issues).

## License

MIT — do whatever you want with it. Attribution appreciated, not required.

---

*Made for streamers who'd rather play than scrub through 5 hours of VOD.*
