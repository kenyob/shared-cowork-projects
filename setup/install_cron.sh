#!/bin/bash
# install_cron.sh — Install the Cowork heartbeat cron on this machine
# ──────────────────────────────────────────────────────────────────
# Auto-detects your Cowork root from .env, installs a cron entry
# that writes a heartbeat file every 30 minutes so you can monitor
# sync health across machines.
#
# Usage:
#   bash setup/install_cron.sh
# ──────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi

COWORK_FOLDER_NAME="${COWORK_FOLDER_NAME:-shared-cowork-projects}"
SYNC_METHOD="${SYNC_METHOD:-icloud}"
HEARTBEAT_CRON="${HEARTBEAT_CRON:-0,30 * * * *}"

case "$SYNC_METHOD" in
  icloud)   COWORK_ROOT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/$COWORK_FOLDER_NAME" ;;
  dropbox)  COWORK_ROOT="$HOME/Dropbox/$COWORK_FOLDER_NAME" ;;
  *)        COWORK_ROOT="$HOME/$COWORK_FOLDER_NAME" ;;
esac

SYNC_TEST="$COWORK_ROOT/_skills/sync_test.py"
LOG="/tmp/cowork-sync-health.log"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Cowork Heartbeat — Cron Installer"
echo "  Machine : $(hostname)"
echo "  Schedule: $HEARTBEAT_CRON"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -f "$SYNC_TEST" ]; then
  echo "❌ sync_test.py not found at: $SYNC_TEST"
  echo "   Run setup/scaffold.sh first to copy scripts into your Cowork folder."
  exit 1
fi

# Remove any existing cowork entry, add fresh one
CRON_LINE="$HEARTBEAT_CRON /usr/bin/python3 \"$SYNC_TEST\" --heartbeat >> \"$LOG\" 2>&1"
(crontab -l 2>/dev/null | grep -v "sync_test.py"; echo "$CRON_LINE") | crontab -

echo "✅ Cron installed:"
echo "   $CRON_LINE"
echo ""
echo "  Verify:        crontab -l | grep sync_test"
echo "  Watch log:     tail -f $LOG"
echo "  Run now:       python3 '$SYNC_TEST' --heartbeat"
echo "  Health check:  python3 '$SYNC_TEST' --check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
