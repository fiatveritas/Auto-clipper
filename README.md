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

## Installation

### Windows

#### Step 1: Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download **Python 3.10 or newer**
3. **IMPORTANT**: Check the box that says **"Add Python to PATH"** during installation
4. Click "Install Now"

To verify, open **Command Prompt** (search "cmd" in the Start menu) and type:
```
python --version
```
You should see something like `Python 3.12.x`.

#### Step 2: Install FFmpeg

1. Go to [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Under "Windows", click **"Windows builds from gyan.dev"**
3. Download the **ffmpeg-release-essentials.zip** file
4. Extract the zip file (right-click → Extract All)
5. Inside the extracted folder, find the `bin` folder (e.g., `ffmpeg-7.1-essentials_build\bin`)
6. Copy the full path to that `bin` folder
7. Add it to your system PATH:
   - Search **"Environment Variables"** in the Start menu
   - Click **"Edit the system environment variables"**
   - Click **"Environment Variables..."**
   - Under "System variables", find **Path** and click **Edit**
   - Click **New** and paste the path to the `bin` folder
   - Click OK on all windows

To verify, open a **new** Command Prompt and type:
```
ffmpeg -version
```

#### Step 3: Download and Run Auto-Clipper

Open **Command Prompt** and run these commands one at a time:

```bash
# Download the project
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper

# Create a virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open your browser and go to **http://localhost:8080**

> **Don't have Git?** Download it from [git-scm.com](https://git-scm.com/download/win), or just click the green "Code" button on GitHub and choose "Download ZIP", then extract it.

#### Running It Again Later

```bash
cd Auto-clipper
venv\Scripts\activate
python app.py
```

---

### Mac

#### Step 1: Install Python

Python 3 may already be installed. Check by opening **Terminal** (search in Spotlight) and typing:
```bash
python3 --version
```

If not installed, install it with Homebrew:
```bash
# Install Homebrew (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python
```

Or download directly from [python.org/downloads](https://www.python.org/downloads/).

#### Step 2: Install FFmpeg

```bash
brew install ffmpeg
```

Or if you don't have Homebrew, install it first (see above).

#### Step 3: Download and Run Auto-Clipper

```bash
# Download the project
git clone https://github.com/bendawg2010/Auto-clipper.git
cd Auto-clipper

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open your browser and go to **http://localhost:8080**

#### Optional: Run as a Desktop App

```bash
python desktop.py
```

This opens Auto-Clipper in its own window instead of a browser tab.

#### Optional: Create a Mac App Bundle

```bash
chmod +x create_mac_app.sh
./create_mac_app.sh
```

This creates an **Auto-Clipper.app** on your Desktop that you can double-click to launch.

#### Running It Again Later

```bash
cd Auto-clipper
source venv/bin/activate
python app.py
```

---

### iPhone / iPad

Auto-Clipper is a web app, so you can use it on your iPhone by running it on a computer and accessing it from your phone's browser.

#### Option A: Access from Your Computer (Same Wi-Fi)

1. **Set up and run** Auto-Clipper on your Windows or Mac computer (follow the guides above)
2. Find your computer's local IP address:
   - **Windows**: Open Command Prompt and type `ipconfig` — look for "IPv4 Address" (e.g., `192.168.1.42`)
   - **Mac**: Open Terminal and type `ipconfig getifaddr en0` (e.g., `192.168.1.42`)
3. On your **iPhone**, make sure you're on the **same Wi-Fi** network as your computer
4. Open **Safari** and go to: `http://YOUR_COMPUTER_IP:8080`
   - Example: `http://192.168.1.42:8080`
5. Tap the **Share** button → **"Add to Home Screen"** to create an app icon

> **Note**: Your computer must be running Auto-Clipper for this to work. The phone is just a remote screen.

#### Option B: Add to Home Screen (Bookmark)

Once you have Auto-Clipper open in Safari:

1. Tap the **Share** button (square with arrow)
2. Scroll down and tap **"Add to Home Screen"**
3. Name it **"Auto-Clipper"**
4. Tap **Add**

Now you have an app-like icon on your home screen.

---

## Quick Start (TL;DR)

| Platform | Commands |
|----------|---------|
| **Windows** | `git clone https://github.com/bendawg2010/Auto-clipper.git && cd Auto-clipper && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python app.py` |
| **Mac** | `git clone https://github.com/bendawg2010/Auto-clipper.git && cd Auto-clipper && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python app.py` |
| **iPhone** | Run on computer, open `http://YOUR_IP:8080` in Safari |

Then open **http://localhost:8080** in your browser.

---

## Optional: AI-Powered Analysis

By default, Auto-Clipper uses computer vision (OpenCV) to detect highlights. For smarter detection, you can enable AI analysis:

1. Get a free API key from [x.ai](https://x.ai/)
2. Set it as an environment variable before running:
   ```bash
   # Mac/Linux
   export XAI_API_KEY=your-key-here

   # Windows
   set XAI_API_KEY=your-key-here
   ```

---

## Troubleshooting

### "python is not recognized" (Windows)
Reinstall Python and make sure to check **"Add Python to PATH"**.

### "ffmpeg is not recognized"
Make sure FFmpeg's `bin` folder is added to your system PATH (see Windows Step 2 above). Open a **new** terminal after changing PATH.

### Clips won't download from Twitch
- Make sure the VOD is **public** (not subscriber-only)
- Some VODs may be region-locked or deleted

### Can't connect from iPhone
- Make sure both devices are on the **same Wi-Fi network**
- Check that your firewall isn't blocking port 8080
- Try disabling VPN on both devices

### Port 8080 is already in use
Another app is using port 8080. Close it or change the port in `app.py`.

---

## Tech Stack

- **Backend**: Python / Flask
- **Video Download**: yt-dlp
- **Video Analysis**: OpenCV + NumPy
- **AI Analysis**: Grok Vision API (optional)
- **Clip Extraction**: FFmpeg
- **Frontend**: HTML / CSS / JavaScript
