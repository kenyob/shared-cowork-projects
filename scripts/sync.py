#!/usr/bin/env python3
"""
sync.py — Shared Cowork Projects: iOS Sync
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pushes agents.md files from your local Cowork folders to your
Claude.ai iOS/web projects so mobile Claude sessions stay current.

Reads all config from .env in the Cowork root folder.

Auth methods (in priority order):
  1. ANTHROPIC_API_KEY in .env  → official API (recommended)
  2. Cookie-based auth          → reads from Chrome, fallback only

Usage:
  python3 sync.py setup             # capture auth (run once per machine)
  python3 sync.py push              # push agents.md to all projects
  python3 sync.py push --dry-run    # preview without pushing
  python3 sync.py route-inbox       # route _inbox/ files to projects
  python3 sync.py sync-memory       # copy Claude auto-memory to cowork-shared-memory/
  python3 sync.py sync-memory --dry-run   # preview memory sync

Memory layers — understanding what gets synced:
  agents.md files     → pushed to Claude.ai Projects (iOS/web Claude reads these) ✅
  Claude auto-memory  → local session files; sync-memory copies them to iCloud   ⚠️
  Heartbeat logs      → health monitoring only, not knowledge                     —

  Run sync-memory on each machine after Cowork sessions to keep
  Claude's learned preferences and feedback in sync across machines.
  Set CLAUDE_MEMORY_PATH in .env to your actual Cowork memory folder.
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass

# ── Locate Cowork root and load .env ──────────────────────────────────────────

def find_cowork_root() -> Path:
    """
    Walk up from this script's location to find the .env file.
    Works whether sync.py is run from _skills/ inside the Cowork folder
    or directly from the repo checkout.
    """
    candidate = Path(__file__).parent
    for _ in range(4):
        if (candidate / ".env").exists():
            return candidate
        candidate = candidate.parent
    # Fallback: assume standard iCloud path
    return Path.home() / "Library/Mobile Documents/com~apple~CloudDocs" / os.environ.get("COWORK_FOLDER_NAME", "shared-cowork-projects")

COWORK_ROOT = find_cowork_root()
ENV_FILE    = COWORK_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

COWORK_FOLDER_NAME = os.environ.get("COWORK_FOLDER_NAME", "shared-cowork-projects")
SYNC_METHOD        = os.environ.get("SYNC_METHOD", "icloud")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_ORG_ID      = os.environ.get("CLAUDE_ORG_ID", "")

COOKIES_FILE   = COWORK_ROOT / "_skills" / ".cookies.json"
LOG_FILE       = COWORK_ROOT / "_skills" / "sync.log"
SYNC_STATE     = COWORK_ROOT / "_skills" / ".sync-state.json"
HEARTBEAT_FILE = COWORK_ROOT / "cowork-shared-memory" / "heartbeat-last-run.md"

# Claude auto-memory path — set CLAUDE_MEMORY_PATH in .env to your actual path.
# This is the memory/ folder Claude writes to during Cowork desktop sessions.
# It is NOT in iCloud by default; sync-memory copies it there so other machines see it.
CLAUDE_MEMORY_PATH = Path(os.environ.get("CLAUDE_MEMORY_PATH", "")).expanduser() if os.environ.get("CLAUDE_MEMORY_PATH") else None
MEMORY_SYNC_DEST   = COWORK_ROOT / "cowork-shared-memory" / "claude-memory"

# ── Load project registry from .env ──────────────────────────────────────────

def load_projects() -> dict:
    """
    Build project registry from .env entries like:
      PROJECT_1_NAME=My Project
      PROJECT_1_ID=uuid-here
      PROJECT_1_FOLDER=01-Projects/my-project
      PROJECT_1_AGENTS_FILE=agents.md
    """
    projects = {}
    n = 1
    while True:
        name   = os.environ.get(f"PROJECT_{n}_NAME")
        pid    = os.environ.get(f"PROJECT_{n}_ID")
        folder = os.environ.get(f"PROJECT_{n}_FOLDER")
        agents = os.environ.get(f"PROJECT_{n}_AGENTS_FILE", "agents.md")
        if not name or not pid:
            break
        key = name.lower().replace(" ", "_")
        projects[key] = {
            "name": name,
            "project_id": pid,
            "cowork_folder": COWORK_ROOT / folder if folder else None,
            "push_files": [agents],
        }
        n += 1

    if not projects:
        log("WARNING: No projects found in .env. Add PROJECT_1_NAME, PROJECT_1_ID, etc.")
    return projects

PROJECTS = load_projects()

# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── Auth: API key (preferred) ─────────────────────────────────────────────────

def get_session_api():
    """Build a requests.Session using the official Anthropic API key."""
    import requests
    session = requests.Session()
    session.headers.update({
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "User-Agent": "shared-cowork-projects/1.0",
    })
    return session

def get_org_id_api(session) -> str:
    """Get org ID via official API, falls back to cookie path if endpoint unavailable."""
    resp = session.get("https://api.anthropic.com/v1/organizations", timeout=10)
    if resp.status_code == 404:
        return get_org_id_cookie(get_session_cookie())
    resp.raise_for_status()
    orgs = resp.json()
    if isinstance(orgs, list) and orgs:
        return orgs[0]["uuid"]
    raise ValueError(f"Could not find org ID. Response: {resp.text[:200]}")

# ── Auth: Cookie fallback ─────────────────────────────────────────────────────

def setup_cookies():
    """Extract claude.ai session cookies from the logged-in Chrome browser."""
    try:
        import sqlite3, shutil, tempfile
        cookie_dbs = [
            Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies",
            Path.home() / "Library/Application Support/Google/Chrome/Profile 1/Cookies",
            Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies",
        ]
        cookies = []
        for db_path in cookie_dbs:
            if not db_path.exists():
                continue
            tmp = tempfile.mktemp(suffix=".db")
            shutil.copy2(db_path, tmp)
            conn = sqlite3.connect(tmp)
            cur = conn.execute(
                "SELECT name, value, host_key, path, expires_utc, is_secure "
                "FROM cookies WHERE host_key LIKE '%claude.ai%'"
            )
            for row in cur.fetchall():
                cookies.append({
                    "name": row[0], "value": row[1],
                    "domain": row[2], "path": row[3],
                    "expires": row[4], "secure": bool(row[5]),
                })
            conn.close()
            Path(tmp).unlink(missing_ok=True)
            if cookies:
                break

        if not cookies:
            print("No claude.ai cookies found.")
            print("Open Chrome and log into claude.ai, then run setup again.")
            return

        COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
        print(f"✓ Saved {len(cookies)} cookies to {COOKIES_FILE}")
    except Exception as e:
        print(f"Error reading Chrome cookies: {e}")
        print("Try closing Chrome first, then run setup again.")

def get_session_cookie():
    """Build a requests.Session from saved cookies."""
    import requests
    if not COOKIES_FILE.exists():
        raise FileNotFoundError(
            f"No cookies found at {COOKIES_FILE}. Run: python3 sync.py setup"
        )
    cookies = json.loads(COOKIES_FILE.read_text())
    session = requests.Session()
    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c.get("domain", ".claude.ai"))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://claude.ai/",
        "Origin": "https://claude.ai",
        "anthropic-client-version": "0",  # Required — missing causes 403
    })
    return session

def get_org_id_cookie(session) -> str:
    """Get org ID from claude.ai via cookie session."""
    resp = session.get("https://claude.ai/api/organizations", timeout=10)
    resp.raise_for_status()
    orgs = resp.json()
    if isinstance(orgs, list) and orgs:
        return orgs[0]["uuid"]
    raise ValueError(f"Could not find org ID. Response: {resp.text[:200]}")

# ── Session factory ────────────────────────────────────────────────────────────

def get_auth():
    """Returns (session, org_id) using the best available auth method."""
    if ANTHROPIC_API_KEY:
        try:
            session = get_session_api()
            org_id = CLAUDE_ORG_ID or get_org_id_api(session)
            log(f"Auth: API key  |  Org: {org_id}")
            return session, org_id
        except Exception as e:
            log(f"API key auth failed ({e}), falling back to cookies...")

    try:
        session = get_session_cookie()
        org_id = CLAUDE_ORG_ID or get_org_id_cookie(session)
        log(f"Auth: cookies  |  Org: {org_id}")
        return session, org_id
    except Exception as e:
        raise RuntimeError(
            f"Auth failed: {e}\n"
            "Run: python3 sync.py setup   (to refresh cookies)\n"
            "Or set ANTHROPIC_API_KEY in your .env file."
        )

# ── Claude.ai Project API ─────────────────────────────────────────────────────

def list_project_docs(session, org_id, project_id) -> list:
    url = f"https://claude.ai/api/organizations/{org_id}/projects/{project_id}/docs"
    resp = session.get(url)
    return resp.json() if resp.status_code == 200 else []

def delete_project_doc(session, org_id, project_id, doc_id):
    url = f"https://claude.ai/api/organizations/{org_id}/projects/{project_id}/docs/{doc_id}"
    resp = session.delete(url)
    return resp.status_code in (200, 204)

def upload_project_doc(session, org_id, project_id, filename, content) -> dict:
    url = f"https://claude.ai/api/organizations/{org_id}/projects/{project_id}/docs"
    existing = list_project_docs(session, org_id, project_id)
    for doc in existing:
        if doc.get("file_name") == filename or doc.get("name") == filename:
            delete_project_doc(session, org_id, project_id, doc["uuid"])
            time.sleep(0.3)
    payload = {"file_name": filename, "content": content}
    resp = session.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()

# ── Push ──────────────────────────────────────────────────────────────────────

def run_push(dry_run=False):
    session, org_id = get_auth()
    pushed, skipped, failed = 0, 0, 0

    for key, proj in PROJECTS.items():
        folder = proj.get("cowork_folder")
        if not folder or not folder.exists():
            log(f"SKIP {proj['name']}: folder not found ({folder})")
            skipped += 1
            continue

        for fname in proj["push_files"]:
            fpath = folder / fname
            if not fpath.exists():
                fpath_alt = folder / fname.upper() if fname.islower() else folder / fname.lower()
                if fpath_alt.exists():
                    fpath = fpath_alt
                else:
                    log(f"SKIP {proj['name']}/{fname}: file not found")
                    skipped += 1
                    continue

            content = fpath.read_text(encoding="utf-8")
            if len(content) < 50:
                log(f"SKIP {proj['name']}/{fname}: too short ({len(content)} chars)")
                skipped += 1
                continue

            if dry_run:
                log(f"WOULD PUSH {proj['name']}/{fname} ({len(content)} chars)")
                pushed += 1
            else:
                try:
                    upload_project_doc(session, org_id, proj["project_id"], fname, content)
                    log(f"PUSHED {proj['name']}/{fname} ({len(content)} chars)")
                    pushed += 1
                    time.sleep(0.5)
                except Exception as e:
                    log(f"ERROR {proj['name']}/{fname}: {e}")
                    failed += 1

    log(f"Push complete — pushed: {pushed}, skipped: {skipped}, failed: {failed}")
    _write_heartbeat(pushed, skipped, failed, dry_run)

def _write_heartbeat(pushed, skipped, failed, dry_run):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    mode = " (dry-run)" if dry_run else ""
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_FILE.write_text(
        f"# Last Sync Run — {now}{mode}\n"
        f"- Pushed: {pushed}\n"
        f"- Skipped: {skipped}\n"
        f"- Failed: {failed}\n"
    )

# ── Inbox routing ─────────────────────────────────────────────────────────────

def route_inbox():
    inbox   = COWORK_ROOT / "_inbox"
    unrouted = inbox / "_unrouted"
    unrouted.mkdir(parents=True, exist_ok=True)

    files = [f for f in inbox.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        log("Inbox: nothing to route")
        return

    for f in files:
        name_lower = f.name.lower()
        routed = False
        for key, proj in PROJECTS.items():
            keywords = os.environ.get(f"PROJECT_{key.upper()}_KEYWORDS", "").lower().split(",")
            if any(kw.strip() and kw.strip() in name_lower for kw in keywords):
                dest = proj["cowork_folder"] / "_from_inbox"
                dest.mkdir(exist_ok=True)
                f.rename(dest / f.name)
                log(f"Routed {f.name} → {proj['name']}/_from_inbox/")
                routed = True
                break
        if not routed:
            f.rename(unrouted / f.name)
            log(f"Unrouted: {f.name} → _inbox/_unrouted/")

# ── Memory sync ──────────────────────────────────────────────────────────────

def sync_memory(dry_run=False):
    """
    Copy Claude's auto-memory files into cowork-shared-memory/claude-memory/
    so they travel across machines via iCloud (or your chosen sync method).

    Claude auto-memory lives in a session-specific local path — NOT in iCloud.
    This command bridges that gap by copying the files into your synced folder.

    On another machine, Claude picks these up when CLAUDE_MEMORY_PATH points
    to the same cowork-shared-memory/claude-memory/ folder.

    Set in .env:
      CLAUDE_MEMORY_PATH=/path/to/your/Claude/memory/folder
    """
    if not CLAUDE_MEMORY_PATH:
        log(
            "sync-memory: CLAUDE_MEMORY_PATH not set in .env\n"
            "  Add the path to your Claude auto-memory folder, e.g.:\n"
            "  CLAUDE_MEMORY_PATH=~/Library/Application Support/Claude/...spaces.../memory"
        )
        return

    if not CLAUDE_MEMORY_PATH.exists():
        log(f"sync-memory: CLAUDE_MEMORY_PATH not found: {CLAUDE_MEMORY_PATH}")
        log("  Check the path in your .env file.")
        return

    memory_files = list(CLAUDE_MEMORY_PATH.glob("*.md"))
    if not memory_files:
        log(f"sync-memory: no .md files found in {CLAUDE_MEMORY_PATH}")
        return

    machine = _machine_tag()
    dest    = MEMORY_SYNC_DEST / machine
    copied  = 0

    log(f"sync-memory: found {len(memory_files)} memory file(s) in {CLAUDE_MEMORY_PATH}")
    log(f"sync-memory: destination → {dest}")

    for src in sorted(memory_files):
        dst = dest / src.name
        if dry_run:
            log(f"  WOULD COPY {src.name}")
            copied += 1
            continue
        dest.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(src, dst)
        log(f"  COPIED {src.name} ({src.stat().st_size} bytes)")
        copied += 1

    if not dry_run:
        # Write a manifest so other machines know when this was last synced
        manifest = dest / "_sync-manifest.md"
        manifest.write_text(
            f"# Claude Memory Snapshot — {machine}\n\n"
            f"- **Synced:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"- **Source:** `{CLAUDE_MEMORY_PATH}`\n"
            f"- **Files:** {copied}\n\n"
            f"## Files included\n\n"
            + "".join(f"- `{f.name}`\n" for f in sorted(memory_files))
        )

    log(f"sync-memory: {'would copy' if dry_run else 'copied'} {copied} file(s)")
    if dry_run:
        log("  (dry-run — no files written)")


def _machine_tag() -> str:
    """Short uppercase hostname for use as a folder name."""
    import socket
    return socket.gethostname().split(".")[0].upper()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Shared Cowork Projects — iOS Sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("command", choices=["setup", "push", "route-inbox", "sync-memory"])
    parser.add_argument("--dry-run", action="store_true", help="Preview without pushing/copying")
    args = parser.parse_args()

    if args.command == "setup":
        setup_cookies()
    elif args.command == "push":
        run_push(dry_run=args.dry_run)
    elif args.command == "route-inbox":
        route_inbox()
    elif args.command == "sync-memory":
        sync_memory(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
