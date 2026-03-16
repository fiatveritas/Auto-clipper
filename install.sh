#!/bin/bash
# Auto-Clipper - One-Click Mac/Linux Installer

echo ""
echo "  ============================================"
echo "    Auto-Clipper - One-Click Installer"
echo "  ============================================"
echo ""

# Detect OS
IS_MAC=false
IS_LINUX=false
if [[ "$(uname)" == "Darwin" ]]; then
    IS_MAC=true
elif [[ "$(uname)" == "Linux" ]]; then
    IS_LINUX=true
fi

# ──────────────────────────────────────────────
# Step 1: Package manager & system dependencies
# ──────────────────────────────────────────────
if $IS_MAC; then
    echo "[1/6] Checking for Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo ""
        echo "  Homebrew is not installed. Installing now..."
        echo "  (You may need to enter your Mac password)"
        echo ""
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Add brew to PATH for this session
        if [ -f /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile 2>/dev/null
        elif [ -f /usr/local/bin/brew ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi

        if ! command -v brew &> /dev/null; then
            echo ""
            echo "  Homebrew installation may need you to restart Terminal."
            echo "  Close this window, open a new Terminal, and run this script again."
            echo ""
            exit 1
        fi
    fi
    echo "  Found Homebrew $(brew --version | head -1)"

    echo ""
    echo "[2/6] Installing Python, Git, and FFmpeg..."
    brew install python git ffmpeg 2>/dev/null
else
    echo "[1/6] Checking system package manager..."
    if command -v apt-get &> /dev/null; then
        echo "  Found apt (Debian/Ubuntu)"
        echo ""
        echo "[2/6] Installing Python, Git, and FFmpeg..."
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-venv python3-pip git ffmpeg 2>/dev/null
    elif command -v dnf &> /dev/null; then
        echo "  Found dnf (Fedora/RHEL)"
        echo ""
        echo "[2/6] Installing Python, Git, and FFmpeg..."
        sudo dnf install -y python3 python3-pip git ffmpeg 2>/dev/null
    elif command -v pacman &> /dev/null; then
        echo "  Found pacman (Arch)"
        echo ""
        echo "[2/6] Installing Python, Git, and FFmpeg..."
        sudo pacman -S --noconfirm python python-pip git ffmpeg 2>/dev/null
    else
        echo "  No supported package manager found."
        echo "  Please install python3, git, and ffmpeg manually."
        exit 1
    fi
fi

# Verify core dependencies
MISSING=""
command -v python3 &> /dev/null || MISSING="$MISSING python3"
command -v git &> /dev/null || MISSING="$MISSING git"
command -v ffmpeg &> /dev/null || MISSING="$MISSING ffmpeg"

if [ -n "$MISSING" ]; then
    echo ""
    echo "  ERROR: Failed to install:$MISSING"
    echo "  Please install them manually and re-run this script."
    exit 1
fi

echo "  Found Python $(python3 --version 2>&1 | cut -d' ' -f2)"
echo "  Found Git $(git --version | cut -d' ' -f3)"
echo "  Found FFmpeg $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3)"

# ──────────────────────────────────────────────
# Step 3: Virtual environment
# ──────────────────────────────────────────────
echo ""
echo "[3/6] Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "  Failed to create virtual environment."
        exit 1
    fi
    echo "  Created virtual environment"
else
    echo "  Virtual environment already exists"
fi

source venv/bin/activate

# ──────────────────────────────────────────────
# Step 4: Core dependencies
# ──────────────────────────────────────────────
echo ""
echo "[4/6] Installing core dependencies..."
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "  Failed to install core dependencies."
    exit 1
fi
echo "  Core dependencies installed"

# ──────────────────────────────────────────────
# Step 5: Optional enhanced features
# ──────────────────────────────────────────────
echo ""
echo "[5/6] Optional features..."
echo ""
echo "  Auto-Clipper supports optional enhanced features."
echo "  You can install them now or skip and add them later."
echo ""

# --- Feature: openWakeWord (real-time voice trigger detection) ---
echo "  ┌──────────────────────────────────────────────┐"
echo "  │  [A] openWakeWord - Real-Time Voice Triggers │"
echo "  │      Detects 'clip that' in real-time with   │"
echo "  │      near-zero CPU usage. Great for live      │"
echo "  │      streaming and always-on monitoring.      │"
echo "  └──────────────────────────────────────────────┘"
read -r -p "  Install openWakeWord? [y/N] " INSTALL_WAKE
echo ""

# --- Feature: WhisperX (precise word-level timestamps) ---
echo "  ┌──────────────────────────────────────────────┐"
echo "  │  [B] WhisperX - Precise Word Timestamps      │"
echo "  │      Adds phoneme-level alignment for more   │"
echo "  │      accurate clip trigger detection.         │"
echo "  │      Requires ~500MB additional download.     │"
echo "  └──────────────────────────────────────────────┘"
read -r -p "  Install WhisperX? [y/N] " INSTALL_WHISPERX
echo ""

# --- Feature: Audio waveform visualization ---
echo "  ┌──────────────────────────────────────────────┐"
echo "  │  [C] librosa - Audio Waveform Visualization  │"
echo "  │      Generates visual waveforms on the clip   │"
echo "  │      timeline. Helps identify loud moments.   │"
echo "  └──────────────────────────────────────────────┘"
read -r -p "  Install librosa (waveform viz)? [y/N] " INSTALL_LIBROSA
echo ""

OPTIONAL_INSTALLED=""
OPTIONAL_SKIPPED=""

if [[ "$INSTALL_WAKE" =~ ^[Yy]$ ]]; then
    echo "  Installing openWakeWord..."
    pip install openwakeword --quiet 2>/dev/null
    if [ $? -eq 0 ]; then
        OPTIONAL_INSTALLED="$OPTIONAL_INSTALLED openWakeWord"
        echo "  openWakeWord installed"
    else
        echo "  WARNING: openWakeWord install failed (may need manual setup)"
        OPTIONAL_SKIPPED="$OPTIONAL_SKIPPED openWakeWord(failed)"
    fi
else
    OPTIONAL_SKIPPED="$OPTIONAL_SKIPPED openWakeWord"
fi

if [[ "$INSTALL_WHISPERX" =~ ^[Yy]$ ]]; then
    echo "  Installing WhisperX..."
    pip install whisperx --quiet 2>/dev/null
    if [ $? -eq 0 ]; then
        OPTIONAL_INSTALLED="$OPTIONAL_INSTALLED WhisperX"
        echo "  WhisperX installed"
    else
        echo "  WARNING: WhisperX install failed (may need manual setup)"
        OPTIONAL_SKIPPED="$OPTIONAL_SKIPPED WhisperX(failed)"
    fi
else
    OPTIONAL_SKIPPED="$OPTIONAL_SKIPPED WhisperX"
fi

if [[ "$INSTALL_LIBROSA" =~ ^[Yy]$ ]]; then
    echo "  Installing librosa..."
    pip install librosa --quiet 2>/dev/null
    if [ $? -eq 0 ]; then
        OPTIONAL_INSTALLED="$OPTIONAL_INSTALLED librosa"
        echo "  librosa installed"
    else
        echo "  WARNING: librosa install failed (may need manual setup)"
        OPTIONAL_SKIPPED="$OPTIONAL_SKIPPED librosa(failed)"
    fi
else
    OPTIONAL_SKIPPED="$OPTIONAL_SKIPPED librosa"
fi

# ──────────────────────────────────────────────
# Step 6: Verify installation
# ──────────────────────────────────────────────
echo ""
echo "[6/6] Verifying installation..."

VERIFY_PASS=true

# Check faster-whisper (clip trigger detection)
python3 -c "import faster_whisper; print('  faster-whisper: OK (clip trigger detection)')" 2>/dev/null
if [ $? -ne 0 ]; then
    python3 -c "import whisper; print('  openai-whisper: OK (clip trigger detection, slower fallback)')" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "  WARNING: No speech-to-text backend found"
        echo "           'Clip That' voice detection will not work"
        VERIFY_PASS=false
    fi
fi

# Check Flask (web UI)
python3 -c "import flask; print('  Flask: OK (web UI)')" 2>/dev/null || echo "  ERROR: Flask not found"

# Check yt-dlp (VOD downloads)
python3 -c "import yt_dlp; print('  yt-dlp: OK (VOD downloads)')" 2>/dev/null || echo "  ERROR: yt-dlp not found"

# Check OpenCV (video processing)
python3 -c "import cv2; print('  OpenCV: OK (video processing)')" 2>/dev/null || echo "  ERROR: OpenCV not found"

# Check YOLO (object detection)
python3 -c "import ultralytics; print('  YOLO/ultralytics: OK (object detection)')" 2>/dev/null || echo "  WARNING: ultralytics not found (AI detection disabled)"

# Check optional features
python3 -c "import openwakeword; print('  openWakeWord: OK (real-time voice triggers)')" 2>/dev/null
python3 -c "import whisperx; print('  WhisperX: OK (precise word timestamps)')" 2>/dev/null
python3 -c "import librosa; print('  librosa: OK (audio waveform visualization)')" 2>/dev/null

# FFmpeg capabilities check
FFMPEG_HW=""
if ffmpeg -hwaccels 2>/dev/null | grep -q "videotoolbox"; then
    FFMPEG_HW="VideoToolbox (Apple HW accel)"
elif ffmpeg -hwaccels 2>/dev/null | grep -q "nvenc\|cuda"; then
    FFMPEG_HW="NVENC/CUDA (NVIDIA HW accel)"
elif ffmpeg -hwaccels 2>/dev/null | grep -q "vaapi"; then
    FFMPEG_HW="VAAPI (Linux HW accel)"
fi
if [ -n "$FFMPEG_HW" ]; then
    echo "  FFmpeg HW Accel: $FFMPEG_HW"
fi

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
echo ""
echo "  ============================================"
echo "    Installation Complete!"
echo "  ============================================"
echo ""
echo "  Core features installed:"
echo "    - Video analysis (motion, scene, audio)"
echo "    - 'Clip That' voice trigger detection"
echo "    - VOD download & clip extraction"
echo "    - Web UI with timeline & clip manager"
echo "    - Keyboard shortcut clipping (Ctrl+Shift+C)"
echo "    - Watch folder auto-detection"
echo ""

if [ -n "$OPTIONAL_INSTALLED" ]; then
    echo "  Optional features installed:"
    for feat in $OPTIONAL_INSTALLED; do
        echo "    + $feat"
    done
    echo ""
fi

if [ -n "$OPTIONAL_SKIPPED" ]; then
    echo "  Optional features skipped (install later with pip):"
    for feat in $OPTIONAL_SKIPPED; do
        echo "    - $feat"
    done
    echo ""
fi

echo "  To run Auto-Clipper:"
echo "    ./run.sh"
echo ""
echo "  Or to create a desktop app:"
echo "    chmod +x create_mac_app.sh"
echo "    ./create_mac_app.sh"
echo ""
echo "  To add optional features later:"
echo "    source venv/bin/activate"
echo "    pip install openwakeword    # real-time voice triggers"
echo "    pip install whisperx        # precise word timestamps"
echo "    pip install librosa         # audio waveform timeline"
echo ""
