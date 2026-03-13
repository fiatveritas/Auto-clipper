#!/bin/bash
# Creates a macOS .app bundle for Arc Raiders Auto-Clipper
# Run this once: ./create_mac_app.sh

APP_NAME="Arc Raiders Clipper"
APP_DIR="$HOME/Desktop/$APP_NAME.app"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Creating $APP_NAME.app on your Desktop..."

# Create .app bundle structure
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create the executable launcher
cat > "$APP_DIR/Contents/MacOS/launcher" << 'LAUNCHER'
#!/bin/bash
DIR="$(cd "$(dirname "$0")/../../.." && pwd)"

LAUNCHER

# Append the project directory (needs to be dynamic)
cat >> "$APP_DIR/Contents/MacOS/launcher" << LAUNCHER
PROJECT_DIR="$PROJECT_DIR"
LAUNCHER

cat >> "$APP_DIR/Contents/MacOS/launcher" << 'LAUNCHER'
cd "$PROJECT_DIR"

# Find Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v /opt/homebrew/bin/python3 &>/dev/null; then
    PYTHON=/opt/homebrew/bin/python3
else
    osascript -e 'display dialog "Python 3 not found.\n\nOpen Terminal and run:\nbrew install python" with title "Auto-Clipper" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

if ! command -v ffmpeg &>/dev/null && ! command -v /opt/homebrew/bin/ffmpeg &>/dev/null; then
    osascript -e 'display dialog "FFmpeg not found.\n\nOpen Terminal and run:\nbrew install ffmpeg" with title "Auto-Clipper" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Setup venv on first run
if [ ! -d "venv" ]; then
    osascript -e 'display notification "First run - installing dependencies..." with title "Auto-Clipper"'
    $PYTHON -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Kill any existing instance
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Open browser
(sleep 2 && open "http://localhost:8080") &

# Run server (keep Terminal-like window open)
python3 app.py
LAUNCHER

chmod +x "$APP_DIR/Contents/MacOS/launcher"

# Create Info.plist
cat > "$APP_DIR/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.autoclipper.arcraiders</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

# Generate an app icon (purple crosshair on dark background)
python3 - << 'PYICON'
from PIL import Image, ImageDraw, ImageFont
import os, sys

sizes = [16, 32, 64, 128, 256, 512, 1024]
img = Image.new('RGBA', (1024, 1024), (14, 14, 16, 255))
draw = ImageDraw.Draw(img)

# Background circle
draw.ellipse([100, 100, 924, 924], fill=(24, 24, 27, 255))
draw.ellipse([120, 120, 904, 904], fill=(30, 30, 35, 255))

# Purple crosshair
purple = (145, 71, 255, 255)
light_purple = (191, 148, 255, 255)

# Crosshair lines
draw.rectangle([490, 200, 534, 450], fill=purple)
draw.rectangle([490, 574, 534, 824], fill=purple)
draw.rectangle([200, 490, 450, 534], fill=purple)
draw.rectangle([574, 490, 824, 534], fill=purple)

# Center dot
draw.ellipse([462, 462, 562, 562], fill=light_purple)
draw.ellipse([480, 480, 544, 544], fill=purple)

# Corner brackets (like a viewfinder)
bw = 12
# Top-left
draw.rectangle([200, 200, 200+80, 200+bw], fill=light_purple)
draw.rectangle([200, 200, 200+bw, 200+80], fill=light_purple)
# Top-right
draw.rectangle([824-80, 200, 824, 200+bw], fill=light_purple)
draw.rectangle([824-bw, 200, 824, 200+80], fill=light_purple)
# Bottom-left
draw.rectangle([200, 824-bw, 200+80, 824], fill=light_purple)
draw.rectangle([200, 824-80, 200+bw, 824], fill=light_purple)
# Bottom-right
draw.rectangle([824-80, 824-bw, 824, 824], fill=light_purple)
draw.rectangle([824-bw, 824-80, 824, 824], fill=light_purple)

# Save as iconset
app_dir = sys.argv[1] if len(sys.argv) > 1 else "."
iconset_dir = os.path.join(app_dir, "Contents", "Resources", "AppIcon.iconset")
os.makedirs(iconset_dir, exist_ok=True)

for size in sizes:
    resized = img.resize((size, size), Image.LANCZOS)
    resized.save(os.path.join(iconset_dir, f"icon_{size}x{size}.png"))
    if size <= 512:
        resized2x = img.resize((size*2, size*2), Image.LANCZOS)
        resized2x.save(os.path.join(iconset_dir, f"icon_{size}x{size}@2x.png"))

print("Icon images created")
PYICON

# Try to create .icns from iconset (requires macOS)
if command -v iconutil &>/dev/null; then
    iconutil -c icns "$APP_DIR/Contents/Resources/AppIcon.iconset" -o "$APP_DIR/Contents/Resources/AppIcon.icns" 2>/dev/null
    rm -rf "$APP_DIR/Contents/Resources/AppIcon.iconset"
    echo "App icon created!"
else
    echo "Note: iconutil not available, app will use default icon"
fi

echo ""
echo "======================================"
echo "  $APP_NAME.app created on your Desktop!"
echo "  Double-click it to launch."
echo "======================================"
echo ""
echo "Note: On first launch macOS may ask you to allow it."
echo "If it says 'damaged', run in Terminal:"
echo "  xattr -cr ~/Desktop/Arc\\ Raiders\\ Clipper.app"
