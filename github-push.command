#!/bin/bash
# github-push.command — shared-cowork-projects v0.8.1-beta
# ─────────────────────────────────────────────────────────
# Double-click this in Finder to initialize git and push to GitHub.
#
# PREREQUISITE: Create the empty repo first at:
#   https://github.com/kenyob/shared-cowork-projects
#   (empty — no README, no .gitignore, no license)
# ─────────────────────────────────────────────────────────

set -e

REPO_DIR="/Volumes/HomeX/bkenyonmini/Development/Active/Shared-CoWork-Projects"
REMOTE="https://github.com/kenyob/shared-cowork-projects.git"
VERSION="0.8.1-beta"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  shared-cowork-projects v$VERSION → GitHub"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$REPO_DIR"

# Remove any partial .git from previous attempts
if [ -d ".git" ]; then
  echo "▶ Removing previous incomplete git folder..."
  rm -rf .git
fi

echo "▶ Initializing git repo..."
git init
git branch -M main

echo ""
echo "▶ Staging all files..."
git add .
echo ""
git status --short
echo ""

echo "▶ Committing v$VERSION..."
git commit -m "Initial release: shared-cowork-projects v$VERSION

Sync Claude.ai Project context across Mac, iPhone, and iPad automatically.

- sync.py: push agents.md to Claude.ai Projects (API key + cookie auth)
- sync_test.py: cross-machine heartbeat writer and health check monitor
- sync-memory: copy Claude auto-memory to iCloud for multi-machine sync
- scaffold.sh + install_cron.sh: one-command PARA setup for new machines
- cowork-ios-sync.skill: installable Claude Cowork skill
- 48 unit tests, all passing (Python 3.9 / 3.11 / 3.12, macOS CI)
- GitHub Actions CI on every push and PR
- Full README: iOS setup, memory layers, daily workflow, sync caveats
- CHANGELOG, CONTRIBUTING, PR/issue templates

Version: $VERSION"

echo ""
echo "▶ Tagging v$VERSION..."
git tag -a "v$VERSION" -m "Release v$VERSION"

echo ""
echo "▶ Adding remote..."
git remote add origin "$REMOTE"

echo ""
echo "▶ Pushing to GitHub..."
git push -u origin main
git push origin "v$VERSION"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Done! https://github.com/kenyob/shared-cowork-projects"
echo ""
echo "  Recommended next steps:"
echo "  1. Settings → Branches → Add rule → main"
echo "     ✅ Require PR before merging"
echo "     ✅ Require status checks (Tests workflow) to pass"
echo "     ✅ Require at least 1 approval"
echo "  2. Post to r/ClaudeAI — draft is in your conversation with Claude"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Press Enter to close..."
