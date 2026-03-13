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

## Windows Installation

### Step 1: Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the big yellow **"Download Python 3.x.x"** button
3. Open the downloaded file
4. **IMPORTANT: Check the box at the bottom that says "Add python.exe to PATH"**
5. Click **"Install Now"**
6. Wait for it to finish, then click **Close**

To make sure it worked:
- Press the **Windows key**, type **cmd**, and press Enter
- Type `python --version` and press Enter
- You should see something like `Python 3.12.x`

### Step 2: Install Git

1. Go to [git-scm.com/download/win](https://git-scm.com/download/win)
2. The download should start automatically — if not, click **"Click here to download manually"**
3. Open the downloaded file
4. Click **Next** through everything — the default settings are fine
5. Click **Install**, then **Finish**

To make sure it worked:
- Open a **new** Command Prompt (close the old one first)
- Type `git --version` and press Enter
- You should see something like `git version 2.x.x`

### Step 3: Download and Install Auto-Clipper

Open a **new** Command Prompt and type these commands one at a time, pressing Enter after each:

```
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
install.bat
```

The installer will automatically:
- Download and install FFmpeg (the video processing tool)
- Create a Python virtual environment
- Install all the app's dependencies

This takes a few minutes. When it says **"Installation Complete!"** you're done.

### Step 4: Run It

Double-click **`run.bat`** inside the Auto-clipper folder.

It will start the server and open your browser automatically to **http://localhost:8080**.

That's it — you should see the Auto-Clipper interface.

### Running It Again Later

Every time you want to use Auto-Clipper, just double-click **`run.bat`**. That's all.

---

## Mac Installation

### Step 1: Open Terminal

1. Press **Command + Space** to open Spotlight
2. Type **Terminal** and press Enter
3. A black/white window will open — this is where you type all the commands below

### Step 2: Download and Install Auto-Clipper

If you don't have Git installed yet, macOS will ask you to install the Command Line Tools when you try to use it. Just click **Install** when it asks.

Type these commands one at a time:

```bash
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
chmod +x install.sh run.sh
./install.sh
```

The installer will automatically:
- Install Homebrew (Mac's package manager) if you don't have it
- Install Python, Git, and FFmpeg
- Create a Python virtual environment
- Install all the app's dependencies

It will ask for your **Mac password** — type it and press Enter. You won't see the characters as you type, that's normal.

This takes a few minutes. When it says **"Installation Complete!"** you're done.

### Step 3: Run It

```bash
./run.sh
```

It will start the server and open your browser automatically to **http://localhost:8080**.

### Running It Again Later

Every time you want to use Auto-Clipper, open Terminal and type:

```bash
cd Auto-clipper
./run.sh
```

### Optional: Create a Desktop App Icon

```bash
chmod +x create_mac_app.sh
./create_mac_app.sh
```

This creates an app on your Desktop you can double-click instead of using Terminal.

---

## How to Use Auto-Clipper

Once the app is running and you see it in your browser:

### 1. Select Your Game

At the top of the page you'll see game buttons — **Arc Raiders** and **War Thunder**. Click the one you're playing. This tells the app what to look for (each game has different kill feeds, explosions, UI elements, etc).

Your selection is saved automatically. Next time you open the app, it remembers.

### 2. Paste a Twitch VOD Link

Go to [twitch.tv](https://www.twitch.tv/) and find the VOD you want to clip. Copy the URL from the address bar — it looks something like:

```
https://www.twitch.tv/videos/2720880233
```

Paste it into the input box and click **Analyze** (or press Enter).

### 3. (Optional) Only Analyze Part of the VOD

If the stream is really long (like 5+ hours), you can save time by only analyzing a specific part:

1. Click **"+ Download specific part (faster)"**
2. Type a start time like `1:30:00` (1 hour 30 minutes in)
3. Type an end time like `2:00:00`
4. Now it will only download and analyze that 30-minute section

### 4. Wait for Analysis

The app will:
1. **Download** the VOD from Twitch (progress bar shows %)
2. **Analyze** every frame looking for exciting moments
3. **Extract** highlight clips automatically

This takes a few minutes depending on VOD length. A 1-hour VOD takes roughly 3-5 minutes.

### 5. Review Your Clips

When analysis is done, you'll see a grid of clips with:
- **Thumbnail preview** of each highlight
- **Label** describing what happened (e.g. "Kill / Elimination", "Explosion / Combat")
- **Timestamp** showing where in the VOD it happened
- **Confidence bar** showing how sure the detector is

### 6. Preview and Trim

Click any clip to open a preview player. From here you can:

- **Watch** the clip to see if it's actually good
- **Trim** it — use the -5s / -1s / +1s / +5s buttons to adjust the start and end points, then click **Re-cut Clip**
- **Download** the clip
- **Make TikTok** — convert it to vertical 9:16 format (see below)

### 7. TikTok / Vertical Video

Click **Make TikTok** to open the TikTok editor:

1. Pick a **preset layout** — most common is "Cam: Top-Right" which puts gameplay on top (70%) and webcam on bottom (30%)
2. If you don't have a webcam, click **No Webcam** for full-screen gameplay
3. For custom layouts, click **Custom** and drag on the frame to draw your own gameplay and webcam regions
4. Check the **Preview** on the right to see how it'll look
5. Click **Export TikTok Video** — it'll process and auto-download the vertical clip

### 8. Delete Clips You Don't Want

Click **Remove** on any clip card to delete it. This just removes it from the current session — it doesn't affect your Twitch VOD.

---

## iPhone / iPad

Auto-Clipper runs on your computer — you view it on your phone through Safari.

### Step 1: Set Up on Your Computer First

Follow the **Windows** or **Mac** guide above to get Auto-Clipper running on your computer.

### Step 2: Find Your Computer's IP Address

**Windows:**
- Open Command Prompt
- Type `ipconfig`
- Look for **"IPv4 Address"** — it's something like `192.168.1.42`

**Mac:**
- Open Terminal
- Type `ipconfig getifaddr en0`
- It will show something like `192.168.1.42`

Write this number down.

### Step 3: Open on Your iPhone

1. Make sure your iPhone is on the **same Wi-Fi** as your computer
2. Open **Safari**
3. In the address bar, type: `http://192.168.1.42:8080` (replace with YOUR number from Step 2)
4. You should see the Auto-Clipper interface

### Step 4: Save It Like an App (Optional)

1. Tap the **Share** button (the square with an arrow pointing up)
2. Scroll down and tap **"Add to Home Screen"**
3. Name it **Auto-Clipper**
4. Tap **Add**

Now you have an icon on your home screen. Just make sure Auto-Clipper is running on your computer when you tap it.

---

## Supported Games

| Game | What It Detects |
|------|----------------|
| **Arc Raiders** | Kill feed text, damage indicators (red vignette), hit markers (crosshair flash), explosions / muzzle flash, Arc enemy glow (blue), combat chaos |
| **War Thunder** | "Target Destroyed" messages, critical hits, bomb / rocket hits, vehicle fires, explosions, air combat, damage indicators |

Each game has its own detection profile tuned for that game's specific colors, UI layout, and visual effects. Adding a new game is just adding a new profile — the detection engine is the same.

---

## Optional: AI-Powered Analysis

By default Auto-Clipper uses computer vision (color detection + motion analysis) to find highlights. It works without any accounts or API keys.

For smarter detection that actually **understands** what's happening in the gameplay:

1. Click **"+ AI Mode (xAI Grok Vision)"** in the app
2. Get a free API key from [x.ai](https://x.ai/)
3. Paste your key into the field

The AI knows the difference between "walking around doing nothing" and "intense firefight with a kill" — computer vision only sees colors and motion. AI mode finds better clips but uses API credits.

Your API key is saved in the app so you only enter it once.

---

## Troubleshooting

**"python is not recognized" (Windows)**
You didn't check "Add python.exe to PATH" during installation. Uninstall Python, download it again, and this time **check that box** at the bottom of the very first installer screen.

**"git is not recognized" (Windows)**
Close your Command Prompt and open a new one. If it still doesn't work, reinstall Git from [git-scm.com](https://git-scm.com/download/win).

**"ffmpeg is not recognized"**
Run `install.bat` (Windows) or `./install.sh` (Mac) again — it will install FFmpeg for you automatically.

**"brew: command not found" (Mac)**
Run `./install.sh` again — it will install Homebrew for you.

**The installer says it worked but `run.bat` doesn't do anything**
Open Command Prompt manually and type:
```
cd Auto-clipper
venv\Scripts\activate
python app.py
```
This will show you any error messages.

**Clips won't download from Twitch**
Make sure the VOD is **public** (not subscriber-only or deleted). Some streamers delete their VODs after a few days.

**Can't connect from iPhone**
- Are both devices on the **same Wi-Fi network**?
- Is Auto-Clipper actually running on your computer? (You need to keep `run.bat` / `run.sh` open)
- Try turning off VPN on both devices
- Windows: Your firewall might be blocking port 8080 — try temporarily disabling it

**Port 8080 already in use**
Something else is using that port. Close other apps, or edit `app.py` and change `port=8080` to `port=8081` (then use `http://localhost:8081` in your browser).

**Analysis found clips but they're all boring / nothing happening**
Try using AI mode — computer vision sometimes picks up false positives. AI mode is much better at understanding what's actually exciting.

**Analysis takes forever**
Use the "Download specific part" option to only analyze a portion of the VOD instead of the whole thing. A 30-minute section analyzes much faster than a 5-hour stream.
