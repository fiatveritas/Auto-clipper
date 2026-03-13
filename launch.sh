#!/bin/bash
# Arc Raiders Auto-Clipper launcher
# Double-click or run from terminal to start

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Check for Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v /opt/homebrew/bin/python3 &>/dev/null; then
    PYTHON=/opt/homebrew/bin/python3
else
    osascript -e 'display dialog "Python 3 not found. Install it with:\n\nbrew install python" with title "Auto-Clipper" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Check for ffmpeg
if ! command -v ffmpeg &>/dev/null && ! command -v /opt/homebrew/bin/ffmpeg &>/dev/null; then
    osascript -e 'display dialog "FFmpeg not found. Install it with:\n\nbrew install ffmpeg" with title "Auto-Clipper" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    osascript -e 'display notification "First run - installing dependencies..." with title "Auto-Clipper"'
    $PYTHON -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Kill any existing instance on port 8080
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Launch as standalone desktop app
python3 desktop.py
