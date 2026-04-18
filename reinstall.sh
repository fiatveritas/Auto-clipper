#!/bin/bash
# Auto-Clipper — Clean Reinstall
#
# Wipes the old repo, re-clones from scratch, and preserves your user data:
#   downloads/   library/   sessions/   uploads/
#   static/clips/   static/thumbnails/
#
# Use when install.sh gets stuck, you hit dependency drift, or you just
# want a pristine copy of the latest code without losing your VOD library.
#
# Usage (from any directory, even inside an old Auto-clipper):
#   ./reinstall.sh
#   OR
#   curl -fsSL https://raw.githubusercontent.com/bendawg2010/Auto-clipper/claude/twitch-clip-analyzer-MPT08/reinstall.sh | bash

set -e

REPO_URL="https://github.com/bendawg2010/Auto-clipper.git"
REPO_NAME="Auto-clipper"
BRANCH="${AUTOCLIPPER_BRANCH:-claude/twitch-clip-analyzer-MPT08}"

echo ""
echo "  ================================================"
echo "    Auto-Clipper — Clean Reinstall"
echo "    (preserves VODs, clips, sessions, library)"
echo "  ================================================"
echo ""

# Figure out where the existing Auto-clipper lives.
# Priority: current dir if it's Auto-clipper, else ./Auto-clipper, else we'll create it.
if [ -d ".git" ] && [ -f "app.py" ]; then
    # We're inside the repo — step up one level.
    cd ..
fi

PARENT="$(pwd)"
TARGET="$PARENT/$REPO_NAME"
BACKUP="$PARENT/.autoclipper-preserve-$(date +%s)"

# ──────────────────────────────────────────────
# Step 1: Back up user data (if an install exists)
# ──────────────────────────────────────────────
if [ -d "$TARGET" ]; then
    echo "[1/5] Backing up your VOD library + clips to"
    echo "      $BACKUP"
    mkdir -p "$BACKUP"

    for dir in downloads library sessions uploads; do
        if [ -d "$TARGET/$dir" ]; then
            echo "      · $dir/"
            mv "$TARGET/$dir" "$BACKUP/"
        fi
    done

    if [ -d "$TARGET/static/clips" ]; then
        echo "      · static/clips/"
        mkdir -p "$BACKUP/static"
        mv "$TARGET/static/clips" "$BACKUP/static/"
    fi

    if [ -d "$TARGET/static/thumbnails" ]; then
        echo "      · static/thumbnails/"
        mkdir -p "$BACKUP/static"
        mv "$TARGET/static/thumbnails" "$BACKUP/static/"
    fi

    # Preserve user config if present
    for f in .env config.json user-profiles.json best.pt arc_raiders_best.pt; do
        if [ -f "$TARGET/$f" ]; then
            echo "      · $f"
            mv "$TARGET/$f" "$BACKUP/"
        fi
    done
else
    echo "[1/5] No existing install found — nothing to back up."
fi

# ──────────────────────────────────────────────
# Step 2: Delete the old repo
# ──────────────────────────────────────────────
if [ -d "$TARGET" ]; then
    echo "[2/5] Removing old install at $TARGET"
    rm -rf "$TARGET"
else
    echo "[2/5] Nothing to remove."
fi

# ──────────────────────────────────────────────
# Step 3: Fresh clone
# ──────────────────────────────────────────────
echo "[3/5] Cloning fresh copy from $REPO_URL (branch: $BRANCH)"
# --depth=1 keeps the clone small (the repo now includes a 21 MB
# best.pt); user can `git fetch --unshallow` later if they need
# the full history.
git clone --branch "$BRANCH" --depth=1 "$REPO_URL" "$TARGET"

# ──────────────────────────────────────────────
# Step 4: Restore user data
# ──────────────────────────────────────────────
if [ -d "$BACKUP" ]; then
    echo "[4/5] Restoring your VOD library + clips"

    for dir in downloads library sessions uploads; do
        if [ -d "$BACKUP/$dir" ]; then
            echo "      · $dir/"
            rm -rf "$TARGET/$dir"
            mv "$BACKUP/$dir" "$TARGET/"
        fi
    done

    if [ -d "$BACKUP/static/clips" ]; then
        echo "      · static/clips/"
        rm -rf "$TARGET/static/clips"
        mkdir -p "$TARGET/static"
        mv "$BACKUP/static/clips" "$TARGET/static/"
    fi

    if [ -d "$BACKUP/static/thumbnails" ]; then
        echo "      · static/thumbnails/"
        rm -rf "$TARGET/static/thumbnails"
        mkdir -p "$TARGET/static"
        mv "$BACKUP/static/thumbnails" "$TARGET/static/"
    fi

    for f in .env config.json user-profiles.json best.pt arc_raiders_best.pt; do
        if [ -f "$BACKUP/$f" ]; then
            echo "      · $f"
            mv "$BACKUP/$f" "$TARGET/"
        fi
    done

    # Clean up the backup directory if it's now empty
    if [ -z "$(ls -A "$BACKUP" 2>/dev/null)" ]; then
        rmdir "$BACKUP"
    else
        echo "      (leftover files kept in $BACKUP just in case)"
    fi
else
    echo "[4/5] No backup to restore — fresh install."
fi

# ──────────────────────────────────────────────
# Step 5: Install + launch
# ──────────────────────────────────────────────
echo "[5/5] Running installer..."
cd "$TARGET"
./install.sh

echo ""
echo "  ================================================"
echo "    ✓ Reinstall complete"
echo "    Launching Auto-Clipper..."
echo "  ================================================"
echo ""

./run.sh
