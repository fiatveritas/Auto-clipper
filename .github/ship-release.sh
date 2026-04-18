#!/bin/bash
# Run after `gh auth login -h github.com -s repo,workflow -w` refreshes your token.
# This pushes the branch and cuts the v0.12.0 release.
set -e

cd "$(dirname "$0")/.."

echo "→ Pushing branch to origin..."
git push origin claude/twitch-clip-analyzer-MPT08

echo "→ Creating v0.12.0 release..."
gh release create v0.12.0 \
  --repo bendawg2010/Auto-clipper \
  --target claude/twitch-clip-analyzer-MPT08 \
  --title "v0.12.0 — CV pipeline rewrite + Clip It voice triggers + landing site" \
  --notes-file .github/RELEASE_NOTES_v0.12.0.md

echo "✓ Done. Release: https://github.com/bendawg2010/Auto-clipper/releases/tag/v0.12.0"
