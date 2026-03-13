#!/bin/bash
# Arc Raiders Auto-Clipper launcher
# Double-click this or run from terminal to start the app

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Check for Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v /opt/homebrew/bin/python3 &>/dev/null; then
    PYTHON=/opt/homebrew/bin/python3
else
    osascript -e 'display dialog "Python 3 not found. Please install it:\n\nbrew install python" with title "Auto-Clipper" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Check for ffmpeg
if ! command -v ffmpeg &>/dev/null && ! command -v /opt/homebrew/bin/ffmpeg &>/dev/null; then
    osascript -e 'display dialog "FFmpeg not found. Please install it:\n\nbrew install ffmpeg" with title "Auto-Clipper" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    osascript -e 'display notification "Setting up for first run..." with title "Auto-Clipper"'
    $PYTHON -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Kill any existing instance on port 8080
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Open browser after a short delay
(sleep 2 && open "http://localhost:8080") &

# Start the server
python3 app.py
