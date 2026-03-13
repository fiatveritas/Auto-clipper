# Arc Raiders Auto-Clipper

Automatically find the best moments in your Twitch VODs — kills, combat, explosions, and more. Paste a link, get highlight clips.

---

## What It Does

1. **Paste** a Twitch VOD link
2. **Wait** while it downloads and analyzes the video
3. **Review** detected highlights with preview thumbnails
4. **Download** the clips you want — or convert them to TikTok vertical format

### What It Detects

- Kill feed / elimination text
- Damage indicators (red vignette)
- Hit markers (crosshair flashes)
- Explosions / muzzle flash
- Arc enemy glow (blue glow)
- Scene chaos (rapid motion during combat)

---

## Windows Installation (From Scratch)

### Step 1: Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the big yellow **"Download Python 3.x.x"** button
3. Open the downloaded file
4. **IMPORTANT: Check the box at the bottom that says "Add python.exe to PATH"**
5. Click **"Install Now"**
6. Wait for it to finish, then click **Close**

**Verify it worked:**
- Press the **Windows key**, type **cmd**, and press Enter
- Type `python --version` and press Enter
- You should see something like `Python 3.12.x`

### Step 2: Install Git

1. Go to [git-scm.com/download/win](https://git-scm.com/download/win)
2. The download should start automatically — if not, click **"Click here to download manually"**
3. Open the downloaded file
4. Click **Next** through everything — the default settings are fine
5. Click **Install**, then **Finish**

**Verify it worked:**
- Open a **new** Command Prompt (close the old one first)
- Type `git --version` and press Enter
- You should see something like `git version 2.x.x`

### Step 3: Install FFmpeg

1. Go to [github.com/BtbN/FFmpeg-Builds/releases](https://github.com/BtbN/FFmpeg-Builds/releases)
2. Scroll down and download **ffmpeg-master-latest-win64-gpl.zip**
3. Right-click the downloaded zip → **Extract All** → **Extract**
4. Open the extracted folder, then open the **bin** folder inside it
5. You should see three files: `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`
6. Copy the full path from the address bar at the top (something like `C:\Users\YourName\Downloads\ffmpeg-master-latest-win64-gpl\bin`)

**Now add it to your PATH so your computer can find it:**

7. Press the **Windows key**, type **Environment Variables**, and click **"Edit the system environment variables"**
8. Click the **"Environment Variables..."** button at the bottom
9. In the bottom section ("System variables"), find **Path** and double-click it
10. Click **New**
11. Paste the path you copied (the one ending in `\bin`)
12. Click **OK** on all three windows

**Verify it worked:**
- Open a **new** Command Prompt (close the old one first)
- Type `ffmpeg -version` and press Enter
- You should see version info, not an error

### Step 4: Download and Run Auto-Clipper

Open a **new** Command Prompt and type these commands one at a time, pressing Enter after each:

```
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Now open your browser (Chrome, Edge, Firefox, whatever) and go to:
**http://localhost:8080**

You should see the Auto-Clipper interface. Paste a Twitch VOD link and go!

### Running It Again Later

Every time you want to use Auto-Clipper again, open Command Prompt and type:
```
cd Auto-clipper
venv\Scripts\activate
python app.py
```

---

## Mac Installation (From Scratch)

### Step 1: Open Terminal

1. Press **Command + Space** to open Spotlight
2. Type **Terminal** and press Enter
3. A black/white window will open — this is where you type all the commands below

### Step 2: Install Homebrew (Mac's Package Manager)

Homebrew makes installing everything else easy. Paste this entire line into Terminal and press Enter:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

- It will ask for your **Mac password** — type it and press Enter (you won't see the characters, that's normal)
- If it asks you to press Enter to continue, press Enter
- Wait for it to finish (this can take a few minutes)

**IMPORTANT — After it finishes**, it will show you two commands to run under "Next steps". They look something like this:
```bash
echo >> /Users/yourname/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellpath)"' >> /Users/yourname/.zprofile
eval "$(/opt/homebrew/bin/brew shellpath)"
```
**Copy and paste those exact commands** it shows you into Terminal and press Enter. This makes Homebrew work.

**Verify it worked:**
```bash
brew --version
```
You should see something like `Homebrew 4.x.x`.

### Step 3: Install Python, Git, and FFmpeg

Now that you have Homebrew, installing everything else is one command:

```bash
brew install python git ffmpeg
```

Wait for it to finish (this can take a few minutes).

**Verify they all worked:**
```bash
python3 --version
git --version
ffmpeg -version
```
Each one should show version info, not an error.

### Step 4: Download and Run Auto-Clipper

Type these commands one at a time, pressing Enter after each:

```bash
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Now open your browser (Safari, Chrome, whatever) and go to:
**http://localhost:8080**

You should see the Auto-Clipper interface. Paste a Twitch VOD link and go!

### Optional: Create a Desktop App

Run this to create an app icon on your Desktop you can double-click:
```bash
chmod +x create_mac_app.sh
./create_mac_app.sh
```

### Running It Again Later

Every time you want to use Auto-Clipper again, open Terminal and type:
```bash
cd Auto-clipper
source venv/bin/activate
python app.py
```

---

## iPhone / iPad

Auto-Clipper runs on your computer — you just view it on your phone through Safari.

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

## Optional: AI-Powered Analysis

By default Auto-Clipper uses computer vision to detect highlights. For smarter detection you can enable AI analysis:

1. Get a free API key from [x.ai](https://x.ai/)
2. Set it before running:

**Windows:**
```
set XAI_API_KEY=your-key-here
python app.py
```

**Mac:**
```bash
export XAI_API_KEY=your-key-here
python app.py
```

---

## Troubleshooting

**"python is not recognized" (Windows)**
Reinstall Python. Make sure you check **"Add python.exe to PATH"** at the bottom of the installer.

**"git is not recognized" (Windows)**
Close your Command Prompt and open a new one. If it still doesn't work, reinstall Git.

**"ffmpeg is not recognized"**
You probably didn't add it to PATH correctly. Go back to the FFmpeg step and redo the PATH part. Make sure you open a **new** Command Prompt after.

**"brew: command not found" (Mac)**
You need to run the "Next steps" commands that Homebrew showed you after installation. If you closed Terminal, reinstall Homebrew.

**Clips won't download from Twitch**
Make sure the VOD is **public** (not subscriber-only or deleted).

**Can't connect from iPhone**
- Are both devices on the **same Wi-Fi network**?
- Is Auto-Clipper actually running on your computer?
- Try turning off VPN on both devices
- Windows: Check if your firewall is blocking port 8080

**Port 8080 already in use**
Something else is using that port. Close other apps or change the port number in `app.py`.
