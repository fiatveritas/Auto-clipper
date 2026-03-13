#!/bin/bash
# Auto-Clipper - One-Click Mac Installer

echo ""
echo "  ============================================"
echo "    Auto-Clipper - One-Click Installer"
echo "  ============================================"
echo ""

# Check for Homebrew
echo "[1/4] Checking for Homebrew..."
if ! command -v brew &> /dev/null; then
    echo ""
    echo "  Homebrew is not installed. Installing now..."
    echo "  (You may need to enter your Mac password)"
    echo ""
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add brew to PATH for this session
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        # Also add to profile so it works next time
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

# Install Python, Git, FFmpeg via Homebrew
echo ""
echo "[2/4] Installing Python, Git, and FFmpeg..."
brew install python git ffmpeg 2>/dev/null

# Verify installations
MISSING=""
command -v python3 &> /dev/null || MISSING="$MISSING python3"
command -v git &> /dev/null || MISSING="$MISSING git"
command -v ffmpeg &> /dev/null || MISSING="$MISSING ffmpeg"

if [ -n "$MISSING" ]; then
    echo ""
    echo "  ERROR: Failed to install:$MISSING"
    echo "  Try running: brew install python git ffmpeg"
    exit 1
fi

echo "  Found Python $(python3 --version 2>&1 | cut -d' ' -f2)"
echo "  Found Git $(git --version | cut -d' ' -f3)"
echo "  Found FFmpeg"

# Create virtual environment
echo ""
echo "[3/4] Setting up Python environment..."
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

# Install dependencies
echo ""
echo "[4/4] Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "  Failed to install dependencies."
    exit 1
fi

echo ""
echo "  ============================================"
echo "    Installation Complete!"
echo "  ============================================"
echo ""
echo "  To run Auto-Clipper:"
echo "    ./run.sh"
echo ""
echo "  Or to create a desktop app:"
echo "    chmod +x create_mac_app.sh"
echo "    ./create_mac_app.sh"
echo ""
