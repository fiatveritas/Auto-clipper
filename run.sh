#!/bin/bash
# Auto-Clipper - Quick Launcher

echo ""
echo "  Starting Auto-Clipper..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "  Not installed yet! Run install.sh first:"
    echo "    chmod +x install.sh"
    echo "    ./install.sh"
    exit 1
fi

# Activate and run
source venv/bin/activate

# ── Preflight (common 'nothing works' root causes) ────────────────────
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "  ⚠  ffmpeg not found on PATH."
    echo "     VOD download + clip extraction will silently fail without it."
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "     Install: brew install ffmpeg"
    else
        echo "     Install: sudo apt install ffmpeg   # or dnf / pacman equivalent"
    fi
    echo ""
fi

# Keep yt-dlp fresh — but only once/week, and in the background so the
# user doesn't wait on a pip round-trip to PyPI every single launch.
# (Twitch breaks yt-dlp's parsing monthly; weekly checks are plenty.)
STAMP=venv/.last-ytdlp-check
if [ ! -f "$STAMP" ] || [ -n "$(find "$STAMP" -mtime +7 -print 2>/dev/null)" ]; then
    (python -m pip install --upgrade yt-dlp --quiet 2>/dev/null && touch "$STAMP") &
fi

# Start server in background
python app.py &
SERVER_PID=$!

# Wait for server to actually bind the port before opening browser
echo "  Waiting for server..."
for i in $(seq 1 30); do
    # Try connecting to the port (works on Mac and Linux)
    if (echo > /dev/tcp/localhost/8080) 2>/dev/null || curl -s http://localhost:8080/ > /dev/null 2>&1; then
        echo "  Server ready!"
        open http://localhost:8080 2>/dev/null || xdg-open http://localhost:8080 2>/dev/null
        break
    fi
    sleep 1
done

# Keep running until server exits
wait $SERVER_PID
