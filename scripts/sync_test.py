#!/usr/bin/env python3
"""
sync_test.py — Health check and heartbeat monitor for shared-cowork-projects

Usage:
    python3 scripts/sync_test.py             # Full health report
    python3 scripts/sync_test.py --check     # Quick status (exit 0 = healthy)
    python3 scripts/sync_test.py --heartbeat # Write heartbeat file (run via cron)

Cron example (fires at :00 and :30 — stagger per machine):
    0,30 * * * * python3 /path/to/shared-cowork-projects/scripts/sync_test.py --heartbeat
"""

import argparse
import json
import os
import platform
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── locate repo root & load .env ────────────────────────────────────────────

def find_repo_root(start: Path) -> Path:
    """Walk up from start until we find a directory containing .env or .env.template."""
    for parent in [start, *start.parents]:
        if (parent / ".env").exists() or (parent / ".env.template").exists():
            return parent
    raise FileNotFoundError(
        "Could not find repo root (.env or .env.template not found). "
        "Run from inside the shared-cowork-projects folder."
    )

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = find_repo_root(SCRIPT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=False)
except ImportError:
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# ── resolve cowork root ──────────────────────────────────────────────────────

def resolve_cowork_root() -> Path:
    """Return the cowork sync folder (where PARA folders live)."""
    override = os.getenv("COWORK_ROOT")
    if override:
        return Path(override).expanduser()

    folder_name = os.getenv("COWORK_FOLDER_NAME", "shared-cowork-projects")
    sync_method = os.getenv("SYNC_METHOD", "icloud").lower()
    home = Path.home()

    if sync_method == "icloud":
        candidate = home / "Library/Mobile Documents/com~apple~CloudDocs" / folder_name
    elif sync_method == "dropbox":
        candidate = home / "Dropbox" / folder_name
        if not candidate.exists():
            candidate = home / "Library/CloudStorage/Dropbox" / folder_name
    elif sync_method == "googledrive":
        import glob
        matches = glob.glob(str(home / "Library/CloudStorage/GoogleDrive-*" / "My Drive" / folder_name))
        candidate = Path(matches[0]) if matches else home / "Google Drive/My Drive" / folder_name
    else:
        candidate = REPO_ROOT

    return candidate if candidate.exists() else REPO_ROOT


COWORK_ROOT   = resolve_cowork_root()
HEARTBEAT_DIR = COWORK_ROOT / "cowork-shared-memory"
LOG_PATH      = REPO_ROOT / "scripts" / "sync-health.log"
NOTIF_PATH    = REPO_ROOT / "scripts" / ".last-notified.json"

# ── helpers ──────────────────────────────────────────────────────────────────

def machine_name() -> str:
    return socket.gethostname().split(".")[0].upper()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def age_str(minutes: float) -> str:
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f}h ago"
    return f"{hours / 24:.1f}d ago"


def log(msg: str):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG_PATH, "a") as f:
        f.write(f"{timestamp}  {msg}\n")

# ── heartbeat ────────────────────────────────────────────────────────────────

def run_heartbeat():
    """Write a heartbeat file and log it. Called by cron."""
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)

    name = machine_name()
    hb_file = HEARTBEAT_DIR / f"heartbeat-{name}.md"
    hb_file.write_text(
        f"# Heartbeat — {name}\n\n"
        f"- **Last seen:** {fmt(now_utc())}\n"
        f"- **Machine:** {name}\n"
        f"- **Platform:** {platform.system()} {platform.release()}\n"
        f"- **Python:** {platform.python_version()}\n"
        f"- **Sync method:** {os.getenv('SYNC_METHOD', 'icloud')}\n"
    )

    log(f"HEARTBEAT {name}")
    print(f"✅  Heartbeat written → {hb_file.name}  ({fmt(now_utc())})")

# ── health check ─────────────────────────────────────────────────────────────

STALE_THRESHOLD_MINUTES = 75  # cron fires every 30 min; 75 = 2.5 missed beats

def check_heartbeats() -> list:
    """Return status for every heartbeat-*.md file found."""
    results = []
    if not HEARTBEAT_DIR.exists():
        return results

    for hb_file in sorted(HEARTBEAT_DIR.glob("heartbeat-*.md")):
        mtime = datetime.fromtimestamp(hb_file.stat().st_mtime, tz=timezone.utc)
        age_m = (now_utc() - mtime).total_seconds() / 60
        name  = hb_file.stem.replace("heartbeat-", "")

        results.append({
            "machine":     name,
            "file":        hb_file.name,
            "last_seen":   fmt(mtime),
            "age_minutes": age_m,
            "status":      "✅ green" if age_m <= STALE_THRESHOLD_MINUTES else "🔴 stale",
        })

    return results


def check_agents_files() -> list:
    """Report whether each PARA folder has an agents.md."""
    results = []
    if not COWORK_ROOT.exists():
        return results

    for folder in sorted(COWORK_ROOT.iterdir()):
        if not folder.is_dir():
            continue
        if folder.name.startswith("_") or folder.name.startswith("."):
            continue
        agents = folder / "agents.md"
        results.append({
            "folder":    folder.name,
            "agents_md": "✅" if agents.exists() else "⚠️  missing",
        })

    return results


def check_env() -> list:
    """Return a list of warnings about missing .env config."""
    warnings = []
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        warnings.append("No .env file found — copy .env.template to .env and fill it in.")
        return warnings

    if not os.getenv("COWORK_FOLDER_NAME"):
        warnings.append("COWORK_FOLDER_NAME not set in .env")
    api_key     = os.getenv("ANTHROPIC_API_KEY", "")
    cookies_ok  = (REPO_ROOT / "scripts" / ".cookies.json").exists()
    if not api_key and not cookies_ok:
        warnings.append("No ANTHROPIC_API_KEY and no .cookies.json — run: python3 scripts/sync.py setup")

    return warnings

# ── reports ──────────────────────────────────────────────────────────────────

def full_report():
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  shared-cowork-projects  —  Health Report")
    print(f"  {fmt(now_utc())}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    warnings = check_env()
    if warnings:
        print("\n⚠️  Config warnings:")
        for w in warnings:
            print(f"   • {w}")

    print(f"\n📁 Cowork root: {COWORK_ROOT}")
    print(f"   Exists: {'✅' if COWORK_ROOT.exists() else '❌ NOT FOUND'}")

    heartbeats = check_heartbeats()
    print(f"\n🔁 Machine heartbeats ({HEARTBEAT_DIR.name}/):")
    if not heartbeats:
        print("   (no heartbeat files found — run --heartbeat on each machine)")
    else:
        for h in heartbeats:
            marker = "◀ this machine" if h["machine"] == machine_name() else ""
            print(f"   {h['status']}  {h['machine']:<14}  {h['last_seen']}  ({age_str(h['age_minutes'])})  {marker}")

    agents = check_agents_files()
    if agents:
        print("\n📄 agents.md coverage:")
        for a in agents:
            print(f"   {a['agents_md']}  {a['folder']}")

    if LOG_PATH.exists():
        lines = LOG_PATH.read_text().splitlines()[-5:]
        print(f"\n📋 Recent log ({LOG_PATH.name}):")
        for line in lines:
            print(f"   {line}")

    print()


def quick_check() -> int:
    """Exit 0 if all machines healthy, 1 if any stale."""
    heartbeats = check_heartbeats()
    if not heartbeats:
        print("⚠️  No heartbeat files found.")
        return 1

    all_ok = True
    for h in heartbeats:
        status = "OK" if h["age_minutes"] <= STALE_THRESHOLD_MINUTES else "STALE"
        print(f"{status}  {h['machine']}  ({age_str(h['age_minutes'])})")
        if status == "STALE":
            all_ok = False

    return 0 if all_ok else 1

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Health check and heartbeat monitor for shared-cowork-projects"
    )
    parser.add_argument("--heartbeat", action="store_true",
                        help="Write a heartbeat file (run from cron)")
    parser.add_argument("--check",     action="store_true",
                        help="Quick status check (exit code reflects health)")
    args = parser.parse_args()

    if args.heartbeat:
        run_heartbeat()
    elif args.check:
        sys.exit(quick_check())
    else:
        full_report()


if __name__ == "__main__":
    main()
