#!/bin/bash
# ============================================================
#  Auto-Clipper — Double-click to install & run
#  Works on Mac. Just double-click this file from Finder.
# ============================================================

# cd into the folder this script lives in (handles any download location)
cd "$(dirname "$0")"

clear
echo ""
echo "  ╔════════════════════════════════════════════╗"
echo "  ║          Auto-Clipper                      ║"
echo "  ╚════════════════════════════════════════════╝"
echo ""

# ---------- Already installed? Just launch ----------
if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    echo "  Already installed! Starting..."
    echo ""
    source venv/bin/activate

    # Preflight: weekly-gated yt-dlp upgrade in the background (don't
    # block startup on a pip round-trip), + synchronous ffmpeg check.
    STAMP=venv/.last-ytdlp-check
    if [ ! -f "$STAMP" ] || [ -n "$(find "$STAMP" -mtime +7 -print 2>/dev/null)" ]; then
        (python -m pip install --upgrade yt-dlp --quiet 2>/dev/null && touch "$STAMP") &
    fi
    if ! command -v ffmpeg >/dev/null 2>&1; then
        echo "  ⚠  ffmpeg missing from PATH. Running: brew install ffmpeg"
        brew install ffmpeg 2>/dev/null || echo "     (brew install failed — install ffmpeg manually)"
    fi

    # Open browser after short delay
    (sleep 2 && open http://localhost:8080 2>/dev/null) &

    python app.py
    exit 0
fi

# ---------- First time: install everything ----------
echo "  First time setup — this takes a few minutes."
echo "  (You may need to enter your Mac password)"
echo ""

# 1. Homebrew
echo "[1/4] Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "  Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add brew to PATH
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile 2>/dev/null
    elif [ -f /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    if ! command -v brew &> /dev/null; then
        echo ""
        echo "  Homebrew needs a Terminal restart."
        echo "  Close this window and double-click Auto-Clipper.command again."
        echo ""
        read -p "  Press Enter to close..."
        exit 1
    fi
fi
echo "  OK"

# 2. Python, Git, FFmpeg
echo "[2/4] Python, Git, FFmpeg..."
brew install python@3.12 git ffmpeg 2>/dev/null
# Also try generic python as fallback
brew install python 2>/dev/null

MISSING=""
# Prefer python3.12 for inference-sdk compatibility (<3.13)
if command -v python3.12 &> /dev/null; then
    PY_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PY_CMD="python3"
else
    MISSING="$MISSING python3"
fi
command -v ffmpeg &> /dev/null || MISSING="$MISSING ffmpeg"

if [ -n "$MISSING" ]; then
    echo ""
    echo "  ERROR: Could not install:$MISSING"
    echo "  Try: brew install python ffmpeg"
    read -p "  Press Enter to close..."
    exit 1
fi
echo "  OK"

# 3. Python virtual environment
echo "[3/4] Python environment..."
$PY_CMD -m venv venv
if [ $? -ne 0 ]; then
    echo "  Failed to create Python environment."
    read -p "  Press Enter to close..."
    exit 1
fi
echo "  OK"

# 4. Dependencies
echo "[4/4] Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "  Failed to install dependencies."
    read -p "  Press Enter to close..."
    exit 1
fi
# Upgrade yt-dlp once at install time — subsequent launches use the
# weekly-gated background upgrade on the fast path above.
pip install --upgrade yt-dlp --quiet
touch venv/.last-ytdlp-check
# Optional: install inference-sdk for Roboflow features (requires Python <3.13)
pip install inference-sdk --quiet 2>/dev/null && echo "  Roboflow SDK installed." || echo "  Note: Roboflow SDK skipped (requires Python <3.13). Other detection methods work fine."
echo "  OK"

# ---------- Done! Launch the app ----------
echo ""
echo "  ============================================"
echo "    Installation complete! Starting app..."
echo "  ============================================"
echo ""
echo "  Next time just double-click Auto-Clipper.command again."
echo ""

# Start server in background
python app.py &
SERVER_PID=$!

# Wait for server to bind the port before opening browser
echo "  Waiting for server..."
for i in $(seq 1 60); do
    if (echo > /dev/tcp/localhost/8080) 2>/dev/null || curl -s http://localhost:8080/ > /dev/null 2>&1; then
        echo "  Server ready!"
        open http://localhost:8080
        break
    fi
    sleep 1
done

wait $SERVER_PID
