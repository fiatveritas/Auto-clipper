#!/bin/bash
# Auto-Clipper — remote install / update
#
# Homebrew-style curl-pipe installer. Files fetched via curl in Terminal
# never receive the com.apple.quarantine xattr, so Gatekeeper never
# intervenes. This is the clean bypass for users without an Apple
# Developer account.
#
# Usage:
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/bendawg2010/Auto-clipper/main/install-remote.sh)"
#
# Or from a checked-out copy:
#   ./install-remote.sh

set -e

REPO_URL="https://github.com/bendawg2010/Auto-clipper.git"
BRANCH="${AUTOCLIPPER_BRANCH:-claude/twitch-clip-analyzer-MPT08}"
TARGET="$HOME/Library/Application Support/Auto-Clipper/Auto-clipper"

banner() {
    cat <<'EOF'

  ==============================================
    Auto-Clipper — One-line installer
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
        # Add brew to PATH for this session
        if [[ -x /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -x /usr/local/bin/brew ]]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
}

banner
ensure_git

# ── clone or update ────────────────────────────────────────────────────
mkdir -p "$(dirname "$TARGET")"
if [ ! -d "$TARGET/.git" ]; then
    echo "→ First install — cloning Auto-clipper to:"
    echo "    $TARGET"
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET"
else
    echo "→ Existing install found — updating"
    cd "$TARGET"
    git fetch --all --prune
    git reset --hard "origin/$BRANCH"
fi

cd "$TARGET"

# ── install system deps (brew/python/ffmpeg) ──────────────────────────
ensure_brew

# ── run the repo's installer (idempotent) ─────────────────────────────
echo ""
echo "→ Running Auto-Clipper installer…"
./install.sh

echo ""
echo "  ==============================================
    ✓ Installed
    Launching Auto-Clipper — browser will open at http://localhost:8080"
echo "  =============================================="
echo ""

./run.sh
