#!/bin/bash
# Auto-Clipper — remote install / clean reinstall
#
# Homebrew-style curl-pipe installer. Files fetched via curl in Terminal
# never receive the com.apple.quarantine xattr, so Gatekeeper never
# intervenes. This is the clean bypass for users without an Apple
# Developer account.
#
# Usage:
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/bendawg2010/Auto-clipper/claude/twitch-clip-analyzer-MPT08/install-remote.sh)"
#
# Behavior:
#   · FIRST RUN  → clones, installs deps, launches
#   · RE-RUN     → CLEAN REINSTALL:
#                    1. backs up user data (VODs, clips, library, .env, weights)
#                    2. wipes the repo + venv + caches
#                    3. fresh clone
#                    4. restores user data
#                    5. installs deps + launches
#
#   Preserved across reinstalls:
#     downloads/   library/   sessions/   uploads/
#     static/clips/   static/thumbnails/
#     .env   config.json   user-profiles.json
#     best.pt   arc_raiders_best.pt
#
#   Wiped every reinstall:
#     venv/   __pycache__/   .git/   all source code

set -e

REPO_URL="https://github.com/bendawg2010/Auto-clipper.git"
BRANCH="${AUTOCLIPPER_BRANCH:-claude/twitch-clip-analyzer-MPT08}"
PARENT="$HOME/Library/Application Support/Auto-Clipper"
TARGET="$PARENT/Auto-clipper"

banner() {
    cat <<'EOF'

  ==============================================
    Auto-Clipper — installer
  ==============================================

EOF
}

ensure_git() {
    if command -v git >/dev/null 2>&1; then
        return
    fi
    echo "→ Git not found — triggering Xcode Command Line Tools install…"
    echo "  (You'll see a system dialog; click Install and wait for it to finish,"
    echo "   then re-run this command.)"
    xcode-select --install || true
    exit 1
}

ensure_brew() {
    if [[ "$(uname)" == "Darwin" ]] && ! command -v brew >/dev/null 2>&1; then
        echo "→ Homebrew not found — installing now (you may be asked for your password)…"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [[ -x /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -x /usr/local/bin/brew ]]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
}

backup_user_data() {
    local backup_dir="$1"
    mkdir -p "$backup_dir"

    # VOD / clip / session directories
    for d in downloads library sessions uploads; do
        if [ -d "$TARGET/$d" ]; then
            echo "      · $d/"
            mv "$TARGET/$d" "$backup_dir/"
        fi
    done

    # static/clips and static/thumbnails
    if [ -d "$TARGET/static/clips" ]; then
        echo "      · static/clips/"
        mkdir -p "$backup_dir/static"
        mv "$TARGET/static/clips" "$backup_dir/static/"
    fi
    if [ -d "$TARGET/static/thumbnails" ]; then
        echo "      · static/thumbnails/"
        mkdir -p "$backup_dir/static"
        mv "$TARGET/static/thumbnails" "$backup_dir/static/"
    fi

    # Config / weights
    for f in .env config.json user-profiles.json best.pt arc_raiders_best.pt; do
        if [ -f "$TARGET/$f" ]; then
            echo "      · $f"
            mv "$TARGET/$f" "$backup_dir/"
        fi
    done
}

restore_user_data() {
    local backup_dir="$1"
    [ -d "$backup_dir" ] || return 0

    for d in downloads library sessions uploads; do
        if [ -d "$backup_dir/$d" ]; then
            echo "      · $d/"
            rm -rf "$TARGET/$d"
            mv "$backup_dir/$d" "$TARGET/"
        fi
    done

    if [ -d "$backup_dir/static/clips" ]; then
        echo "      · static/clips/"
        rm -rf "$TARGET/static/clips"
        mkdir -p "$TARGET/static"
        mv "$backup_dir/static/clips" "$TARGET/static/"
    fi
    if [ -d "$backup_dir/static/thumbnails" ]; then
        echo "      · static/thumbnails/"
        rm -rf "$TARGET/static/thumbnails"
        mkdir -p "$TARGET/static"
        mv "$backup_dir/static/thumbnails" "$TARGET/static/"
    fi

    for f in .env config.json user-profiles.json best.pt arc_raiders_best.pt; do
        if [ -f "$backup_dir/$f" ]; then
            echo "      · $f"
            mv "$backup_dir/$f" "$TARGET/"
        fi
    done

    # Clean up the backup dir if it's empty
    rmdir "$backup_dir/static" 2>/dev/null || true
    rmdir "$backup_dir" 2>/dev/null || true
}

banner
ensure_git

mkdir -p "$PARENT"

# ── branch: first install vs reinstall ────────────────────────────────
if [ ! -d "$TARGET/.git" ]; then
    echo "→ First install — cloning Auto-clipper to:"
    echo "    $TARGET"
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET"
else
    BACKUP="$PARENT/.autoclipper-preserve-$(date +%s)"
    echo "→ Existing install detected — doing a CLEAN reinstall."
    echo "   Your VODs, clips, library, and weights are preserved."
    echo ""
    echo "[1/4] Backing up user data to:"
    echo "      $BACKUP"
    backup_user_data "$BACKUP"

    echo "[2/4] Removing the old install (code, venv, caches)…"
    rm -rf "$TARGET"

    echo "[3/4] Cloning fresh copy from $REPO_URL (branch $BRANCH)…"
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET"

    echo "[4/4] Restoring your data…"
    restore_user_data "$BACKUP"
fi

cd "$TARGET"

# ── system deps ───────────────────────────────────────────────────────
ensure_brew

# ── Python deps + launch ──────────────────────────────────────────────
echo ""
echo "→ Running Auto-Clipper installer…"
./install.sh

echo ""
echo "  =============================================="
echo "    ✓ Installed"
echo "    Launching Auto-Clipper — browser will open at http://localhost:8080"
echo "  =============================================="
echo ""

./run.sh
