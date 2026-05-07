#!/bin/bash
# scaffold.sh — Create your shared-cowork-projects folder structure
# ─────────────────────────────────────────────────────────────────
# Run once on any new Mac to create the PARA folder structure
# inside your chosen sync folder (iCloud Drive by default).
#
# Usage:
#   bash setup/scaffold.sh
# ─────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi

COWORK_FOLDER_NAME="${COWORK_FOLDER_NAME:-shared-cowork-projects}"
SYNC_METHOD="${SYNC_METHOD:-icloud}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Shared Cowork Projects — Scaffold Setup"
echo "  Folder: $COWORK_FOLDER_NAME"
echo "  Sync:   $SYNC_METHOD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

case "$SYNC_METHOD" in
  icloud)
    BASE="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
    if [ ! -d "$BASE" ]; then
      echo "❌ iCloud Drive folder not found at: $BASE"
      echo "   Check System Settings → Apple ID → iCloud → iCloud Drive is ON."
      exit 1
    fi
    ;;
  dropbox)
    BASE="$HOME/Dropbox"
    [ ! -d "$BASE" ] && BASE="$HOME/Library/CloudStorage/Dropbox"
    if [ ! -d "$BASE" ]; then
      echo "❌ Dropbox folder not found. Is Dropbox installed and signed in?"
      exit 1
    fi
    ;;
  googledrive)
    BASE=$(ls -d "$HOME/Library/CloudStorage/GoogleDrive-"*/My\ Drive 2>/dev/null | head -1)
    if [ -z "$BASE" ]; then
      echo "❌ Google Drive folder not found. Is Google Drive for Desktop installed?"
      exit 1
    fi
    ;;
  syncthing|manual)
    echo "▶ Enter the full path to your sync folder:"
    read -r BASE
    if [ ! -d "$BASE" ]; then
      echo "❌ Path not found: $BASE"
      exit 1
    fi
    ;;
  *)
    echo "❌ Unknown SYNC_METHOD: $SYNC_METHOD"
    echo "   Valid options: icloud | dropbox | googledrive | syncthing | manual"
    exit 1
    ;;
esac

COWORK_ROOT="$BASE/$COWORK_FOLDER_NAME"

echo "▶ Will create Cowork folder at:"
echo "  $COWORK_ROOT"
echo ""
read -r -p "  Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "  Cancelled."; exit 0; }
echo ""

echo "▶ Creating PARA folder structure..."
folders=(
  "01-Projects"
  "02-Areas"
  "03-Resources"
  "04-Archive"
  "_inbox/_unrouted"
  "_skills"
  "cowork-shared-memory"
)

for folder in "${folders[@]}"; do
  mkdir -p "$COWORK_ROOT/$folder"
  echo "  ✅ $folder"
done

echo ""
echo "▶ Creating template agents.md files..."
for dir in 01-Projects 02-Areas 03-Resources 04-Archive; do
  if [ ! -f "$COWORK_ROOT/$dir/agents.md" ]; then
    cat > "$COWORK_ROOT/$dir/agents.md" << EOF
# $dir — Agent Context

Describe this area and what Claude should know when working here.

## What this area is
<!-- One sentence: what kind of work lives here? -->

## Current focus
<!-- What are you actively working on in this area? -->

## Key context for Claude
<!-- What does Claude need to know to be useful in this space? -->
EOF
    echo "  ✅ $dir/agents.md"
  else
    echo "  — $dir/agents.md already exists, skipping"
  fi
done

if [ ! -f "$COWORK_ROOT/.env" ]; then
  cp "$SCRIPT_DIR/.env.template" "$COWORK_ROOT/.env"
  echo ""
  echo "  ✅ Copied .env.template → .env"
  echo "  ⚠️  Open $COWORK_ROOT/.env and fill in your project IDs and API key."
fi

echo ""
echo "▶ Copying scripts to $COWORK_ROOT/_skills/..."
cp "$SCRIPT_DIR/scripts/sync.py"       "$COWORK_ROOT/_skills/sync.py"
cp "$SCRIPT_DIR/scripts/sync_test.py"  "$COWORK_ROOT/_skills/sync_test.py"
chmod +x "$COWORK_ROOT/_skills/sync.py"
chmod +x "$COWORK_ROOT/_skills/sync_test.py"
echo "  ✅ sync.py"
echo "  ✅ sync_test.py"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Scaffold complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit $COWORK_ROOT/.env — add your ANTHROPIC_API_KEY and project IDs"
echo "  2. bash setup/install_cron.sh     (installs heartbeat cron)"
echo "  3. python3 scripts/sync.py setup  (if using cookie auth)"
echo "  4. python3 scripts/sync.py push --dry-run"
echo "  5. python3 scripts/sync.py push"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
