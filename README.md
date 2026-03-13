# Auto-Clipper

Automatically find the best moments in your Twitch VODs — kills, combat, explosions, and more. Paste a link, get highlight clips.

**Supports:** Arc Raiders, War Thunder (more coming)

---

## What It Does

1. **Pick** your game from the menu
2. **Paste** a Twitch VOD link
3. **Wait** while it downloads and analyzes the video
4. **Review** detected highlights with preview thumbnails
5. **Download** the clips you want — or convert them to TikTok vertical format

Your settings (game, API key, everything) are saved automatically — even if you close the tab.

---

## Quick Install (Recommended)

Only two things you need to install by hand: **Python** and **Git**. The installer handles everything else.

### Windows

**Step 1:** Install Python from [python.org/downloads](https://www.python.org/downloads/)
- **CHECK THE BOX** that says **"Add python.exe to PATH"** at the bottom of the installer!

**Step 2:** Install Git from [git-scm.com/download/win](https://git-scm.com/download/win)
- Click Next through everything, defaults are fine

**Step 3:** Open Command Prompt and run:
```
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
install.bat
```

**Step 4:** To run it anytime, just double-click **`run.bat`**

That's it. The installer downloads FFmpeg and sets up everything automatically.

### Mac

**Step 1:** Open Terminal (Command + Space, type "Terminal", press Enter)

**Step 2:** Run these commands:
```bash
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
chmod +x install.sh run.sh
./install.sh
```

The installer will set up Homebrew, Python, Git, FFmpeg, and all dependencies automatically. It may ask for your Mac password.

**Step 3:** To run it anytime:
```bash
./run.sh
```

---

## Manual Install (If Quick Install Doesn't Work)

<details>
<summary>Click to expand full manual instructions</summary>

### Windows - Manual

#### Install Python
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the big yellow **"Download Python 3.x.x"** button
3. Open the downloaded file
4. **IMPORTANT: Check the box at the bottom that says "Add python.exe to PATH"**
5. Click **"Install Now"**

#### Install Git
1. Go to [git-scm.com/download/win](https://git-scm.com/download/win)
2. Download and install with default settings

#### Install FFmpeg
1. Go to [github.com/BtbN/FFmpeg-Builds/releases](https://github.com/BtbN/FFmpeg-Builds/releases)
2. Download **ffmpeg-master-latest-win64-gpl.zip**
3. Extract it somewhere (like `C:\ffmpeg`)
4. Add the `bin` folder to your PATH:
   - Windows key → type "Environment Variables" → click it
   - Click "Environment Variables..." at the bottom
   - Find "Path" in System variables → double-click → New
   - Paste the path to the `bin` folder
   - Click OK on all windows

#### Run Auto-Clipper
```
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8080** in your browser.

### Mac - Manual

#### Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Run the "Next steps" commands it shows you after installing.

#### Install dependencies
```bash
brew install python git ffmpeg
```

#### Run Auto-Clipper
```bash
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8080** in your browser.

</details>

---

## iPhone / iPad

Auto-Clipper runs on your computer — you view it on your phone through Safari.

1. Get Auto-Clipper running on your computer first (see above)
2. Find your computer's IP address:
   - **Windows:** Open Command Prompt → type `ipconfig` → look for "IPv4 Address" (something like `192.168.1.42`)
   - **Mac:** Open Terminal → type `ipconfig getifaddr en0`
3. On your iPhone (same Wi-Fi), open Safari and go to `http://192.168.1.42:8080` (use YOUR IP)
4. Optional: Tap Share → "Add to Home Screen" to save it like an app

---

## Supported Games

| Game | What It Detects |
|------|----------------|
| **Arc Raiders** | Kill feed, damage indicators, hit markers, explosions, Arc enemy glow, combat chaos |
| **War Thunder** | Target destroyed, critical hits, bomb hits, vehicle fires, explosions, air kills |

More games can be added — each game has its own detection profile tuned for that game's specific visual elements.

---

## Optional: AI-Powered Analysis

By default Auto-Clipper uses computer vision. For smarter detection, enter an xAI API key in the app (click "AI Mode" to expand the field). Get a free key from [x.ai](https://x.ai/).

The AI actually understands what's happening in your gameplay — not just colors and motion.

---

## Troubleshooting

**"python is not recognized" (Windows)**
Reinstall Python. Make sure you check **"Add python.exe to PATH"** at the bottom of the installer.

**"git is not recognized" (Windows)**
Close your Command Prompt and open a new one. If it still doesn't work, reinstall Git.

**"ffmpeg is not recognized"**
Run `install.bat` (Windows) or `./install.sh` (Mac) again — it will install FFmpeg for you.

**"brew: command not found" (Mac)**
Run the "Next steps" commands that Homebrew showed you after installation, or run `./install.sh` again.

**Clips won't download from Twitch**
Make sure the VOD is **public** (not subscriber-only or deleted).

**Can't connect from iPhone**
- Both devices on the **same Wi-Fi**?
- Is Auto-Clipper running on your computer?
- Windows: Firewall might be blocking port 8080

**Port 8080 already in use**
Something else is using that port. Close other apps or change the port in `app.py`.
