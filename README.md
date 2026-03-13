# Arc Raiders Auto-Clipper

A web app that analyzes your Twitch VODs and automatically finds exciting moments in Arc Raiders gameplay — kills, combat encounters, explosions, and more. Paste your Twitch link, wait for the analysis, then review and download your highlight clips.

## How It Works

1. **Paste** your Twitch VOD link (e.g. `https://www.twitch.tv/videos/2720880233`)
2. **Wait** while the app downloads and analyzes the video
3. **Review** detected highlights — each one gets a preview thumbnail and label
4. **Download** the clips you want to keep

### Detection Methods

The analyzer looks for Arc Raiders-specific gameplay signals:
- **Kill feed / elimination text** — bright UI text in the top-right
- **Damage indicators** — red vignette flashes when taking hits
- **Hit markers** — bright flashes in the crosshair region
- **Explosions / muzzle flash** — orange-yellow bursts
- **Arc enemy glow** — distinctive blue glow from Arc enemies
- **Scene chaos** — rapid motion and brightness changes during combat

## Setup

### Prerequisites
- Python 3.10+
- FFmpeg (for clip extraction)

### Install

```bash
# Clone the repo
git clone <repo-url>
cd Auto-clipper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## Tech Stack

- **Backend**: Flask + Flask-SocketIO (real-time progress updates)
- **Video Download**: yt-dlp (Twitch VOD support)
- **Video Analysis**: OpenCV + NumPy (frame-by-frame color/motion analysis)
- **Clip Extraction**: FFmpeg (fast, high-quality cuts)
- **Frontend**: Vanilla HTML/CSS/JS with Socket.IO
