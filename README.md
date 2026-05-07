# shared-cowork-projects

[![Tests](https://github.com/kenyob/shared-cowork-projects/actions/workflows/test.yml/badge.svg)](https://github.com/kenyob/shared-cowork-projects/actions/workflows/test.yml)
[![Version](https://img.shields.io/badge/version-0.8.1--beta-orange.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

> **Every time you open Claude on your iPhone, it has no idea what you were just working on your Mac.**

Claude.ai Projects let you give Claude persistent context — but that context lives in a text box you have to manually maintain. If you use Claude seriously across multiple machines and iOS devices, keeping that context current is tedious. This repo automates it.

---

## The problem

You've set up Claude Projects on claude.ai. You've written careful context files. But:

- Your iPhone Claude doesn't know about the sprint you started this morning on your Mac
- Your laptop Claude doesn't know you just closed a deal in a client meeting 10 minutes ago
- Every time something changes, you have to manually go update a project context box somewhere
- If you use two Macs, you're not even sure which machine has the "real" version of anything

**shared-cowork-projects** solves this with a folder structure + two Python scripts that run quietly in the background.

---

## What it does

1. **Organizes your Claude context** in a [PARA-style](https://fortelabs.com/blog/para/) folder structure that syncs across your machines via iCloud (or Dropbox, Google Drive, or Syncthing)
2. **Pushes your `agents.md` context files** to your Claude.ai Projects automatically — so your iPhone and iPad Claude stay current without you touching anything
3. **Monitors sync health** across machines with a 30-minute heartbeat so you know when something stops working

You write one `agents.md` per project area (like a briefing for Claude). The sync script handles the rest.

---

## Quick start (5 minutes)

### 1. Clone and configure

```bash
git clone https://github.com/kenyob/shared-cowork-projects.git
cd shared-cowork-projects
cp .env.template .env
```

Open `.env` and fill in:
- Your `ANTHROPIC_API_KEY` (get one at [console.anthropic.com](https://console.anthropic.com))
- Your Claude.ai project IDs (from `claude.ai/project/<id>`)
- Your preferred sync method (default: `icloud`)

### 2. Scaffold your folder structure

```bash
bash setup/scaffold.sh
```

Creates PARA folders inside your sync folder (iCloud Drive by default) and copies the scripts into place. Run once per machine.

### 3. Set up auth

If you added an `ANTHROPIC_API_KEY` in step 1, skip this. Otherwise:

```bash
python3 scripts/sync.py setup   # reads your Claude.ai session from Chrome
```

### 4. Test and push

```bash
python3 scripts/sync.py push --dry-run        # preview what will be pushed
python3 scripts/sync.py push                  # push agents.md files to Claude.ai
python3 scripts/sync.py sync-memory --dry-run # preview Claude auto-memory sync
python3 scripts/sync.py sync-memory           # copy auto-memory to iCloud for other machines
```

### 5. Install the background heartbeat

```bash
bash setup/install_cron.sh
```

Installs a cron job that writes a heartbeat file every 30 minutes and monitors sync health across your machines.

---

## Folder structure

After running `scaffold.sh`:

```
shared-cowork-projects/          ← lives inside iCloud Drive (or Dropbox, etc.)
├── 01-Projects/                 ← Active work with deadlines
│   └── agents.md                ← ← ← This gets pushed to your Claude.ai Project
├── 02-Areas/                    ← Ongoing responsibilities
│   └── agents.md
├── 03-Resources/                ← Reference material, templates
│   └── agents.md
├── 04-Archive/                  ← Completed or inactive work
│   └── agents.md
├── _inbox/                      ← Drop files here from iPhone/iPad
│   └── _unrouted/               ← Files that didn't match any project
├── scripts/
│   ├── sync.py                  ← Pushes agents.md to Claude.ai projects
│   ├── sync_test.py             ← Health check + heartbeat monitor
│   └── .cookies.json            ← Local only, never committed
├── cowork-shared-memory/        ← Cross-machine heartbeat files
├── .env                         ← Your config (never committed)
└── .env.template                ← Committed template — copy this to .env
```

**What gets synced — and what doesn't**

This repo handles **one specific job**: keeping your `agents.md` context files in sync with your Claude.ai Projects so that Claude on your iPhone/iPad has current context. That's it.

It does **not** sync your actual project files (code, docs, Obsidian notes, etc.) between machines. That's a separate concern — use iCloud Drive, Dropbox, Syncthing, or whatever sync method you already rely on for your real files. This repo just sits alongside that and keeps Claude's context layer up to date.

The mental model:
```
Your real files  ──► iCloud / Dropbox / Syncthing  ──► other machines
Your agents.md   ──► sync.py (this repo)           ──► Claude.ai Projects ──► iPhone Claude
```

**What goes in `agents.md`?** Write it like a briefing for Claude: what this area is, what you're working on, key decisions, what context Claude needs to be useful. Claude reads it at the start of every project session. Think of it as a "context file for Claude" — not a sync of your actual work files.

---

## Sync methods

Set `SYNC_METHOD` in `.env`:

| Method | Works on | Notes |
|---|---|---|
| `icloud` | macOS | Default. Zero config if iCloud Drive is enabled. |
| `dropbox` | macOS, Windows, Linux | Dropbox must be installed and signed in. |
| `googledrive` | macOS, Windows | Google Drive for Desktop required. |
| `syncthing` | macOS, Linux, Windows | Great for dev folders — enter path manually in `.env`. |
| `manual` | Any | You manage sync; scripts just read/write locally. |

---

---

## Memory layers — what gets synced and what doesn't

There are three distinct memory layers in this system. Understanding them prevents the most common source of confusion: "why doesn't Claude on my laptop know what it learned on my desktop?"

| Layer | What it is | Synced? | How |
|---|---|---|---|
| `agents.md` files | Your curated project context — what Claude reads at the start of every session | ✅ Yes | `sync.py push` → Claude.ai Projects → all devices |
| Claude auto-memory | Files Claude writes automatically during Cowork sessions (preferences, feedback, learned facts) | ⚠️ Manual | `sync.py sync-memory` → `cowork-shared-memory/` → iCloud |
| Heartbeat logs | Timestamps confirming sync is alive | — | Health monitoring only, not knowledge |

### agents.md — the primary memory layer

This is the memory you actively write and curate. One file per PARA folder, pushed to Claude.ai Projects, available on all devices. Think of it as the briefing Claude reads before every session.

Update it whenever something changes that Claude should always know — a new direction, a key decision, a completed milestone.

### Claude auto-memory — the secondary memory layer

When Claude runs in Cowork on your Mac, it automatically saves things it learns about you: your role, your preferences, feedback you gave it, and project-specific facts. These live in a `memory/` folder on your local machine — **not** in iCloud, not synced anywhere by default.

If you only use one Mac, this isn't a problem. If you use two Macs or want this memory to persist robustly, run:

```bash
python3 scripts/sync.py sync-memory --dry-run   # preview
python3 scripts/sync.py sync-memory             # copy to cowork-shared-memory/
```

This copies your memory files into `cowork-shared-memory/claude-memory/<MACHINE>/` which is inside your iCloud-synced folder, so other machines can see them.

**To set it up**, add your memory path to `.env`:
```
CLAUDE_MEMORY_PATH=~/Library/Application Support/Claude/.../memory
```

To find the exact path: in a Cowork session, ask Claude *"where is your memory folder?"* and it will tell you the full path for that machine.

> **Note:** Auto-memory sync copies files so Claude on another machine *can* read them, but Claude doesn't automatically load another machine's memory files. This is an area where contributions are welcome — a `load-memory` command that merges a remote machine's memory into the local one would complete the picture.

---

## Multi-machine setup

Stagger your cron schedules so machines don't write to iCloud at the same time. Set `HEARTBEAT_CRON` in `.env`:

```
Machine 1 (desktop):   HEARTBEAT_CRON=0,30 * * * *    # fires at :00 and :30
Machine 2 (laptop):    HEARTBEAT_CRON=15,45 * * * *   # fires at :15 and :45
Machine 3:             HEARTBEAT_CRON=7,37 * * * *
```

Check health from any machine:

```bash
python3 scripts/sync_test.py           # full report
python3 scripts/sync_test.py --check   # quick status (exit code 0 = all green)
python3 scripts/sync_test.py --heartbeat  # write heartbeat now (normally run by cron)
```

---

## Auth

**Recommended: API key**

Add to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

`sync.py` uses it automatically. Get a key at [console.anthropic.com](https://console.anthropic.com).

**Fallback: Cookie auth**

If you don't have an API key, `sync.py` reads your Claude.ai session from Chrome:

```bash
python3 scripts/sync.py setup
```

Cookies expire periodically. If you get a `403` error, run `setup` again with Chrome open and logged into claude.ai.

> **Security:** cookies are stored in `scripts/.cookies.json`, which `.gitignore` excludes. Never commit or share this file.

---

---

## iOS setup (iPhone & iPad)

The good news: once your Mac is configured and `sync.py push` has run at least once, **your iPhone and iPad don't need any special setup**. Claude on iOS will automatically have your context the next time you open a Project.

Here's what to do on your iOS devices:

### 1. Install Claude and open your Projects

- Install the [Claude app](https://apps.apple.com/us/app/claude-ai/id6473753684) from the App Store
- Sign in with the same Claude.ai account you use on your Mac
- Tap **Projects** in the bottom nav — you should see the same Projects you set up on your Mac

### 2. Find your Project IDs (do this on desktop, easier)

Your `.env` file needs the UUID for each Claude.ai Project. The easiest way to get these:

1. Open [claude.ai](https://claude.ai) in a desktop browser
2. Click into a Project
3. Look at the URL: `claude.ai/project/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
4. Copy that UUID into your `.env` as `PROJECT_1_ID=...`

> You can also find it on iOS by tapping a Project → Share → Copy Link, then reading the UUID from the link.

### 3. Understand what syncs automatically

Once your Mac cron is running, here's what happens without any action on your part:

```
You update agents.md on Mac
    ↓  (every 30 min, or run sync.py push manually)
sync.py pushes it to Claude.ai Project knowledge
    ↓  (instantly available)
Claude on iPhone reads it at the start of every Project session
```

You don't tap anything on iOS — Claude just has your context. If something feels stale, run `python3 scripts/sync.py push` on your Mac to force an immediate update.

### 4. Drop files into your inbox from iPhone (optional)

> **iCloud only (tested).** Dropbox and Google Drive have iOS apps that can expose folders through the Files app, but the paths differ and this workflow has not been tested with those providers. Syncthing has no official iOS client — if you use Syncthing on Mac, use AirDrop or email-to-self as your iOS → Mac bridge instead.

If you use **iCloud** as your `SYNC_METHOD`, your `_inbox/` folder is accessible directly from iPhone:

1. Open the **Files** app on iPhone
2. Navigate to **iCloud Drive → shared-cowork-projects → _inbox**
3. AirDrop, save, or move any file there
4. Back on your Mac, run: `python3 scripts/sync.py route-inbox` to route it to the right project folder

### 5. Edit agents.md from iPhone (optional)

> **iCloud only (tested).** Same caveat as above — this works out of the box with iCloud. Dropbox/Google Drive may work via their iOS apps but are untested. PRs welcome for verified workflows on other providers.

If you use iCloud, you can read and edit your `agents.md` files directly in the Files app or any iOS text editor (iA Writer, Obsidian Mobile, etc.) that supports iCloud Drive. Changes sync to your Mac automatically via iCloud.

### What iOS can't do

- **iOS can't run the sync scripts** — `sync.py` and `sync_test.py` are Mac-only. The iPhone is purely a consumer of the context that your Mac pushes.
- **The Claude iOS app doesn't expose Project IDs in a URL** — get them from the desktop browser.
- **Cookie auth doesn't work on iOS** — the cookie capture reads from Chrome on macOS. If you're API-key-only, this isn't an issue.

---

## Keeping iOS knowledge — and getting it back to your Mac

This is the part most people overlook. The sync runs **Mac → iOS** automatically. But anything you learn, decide, or create in an iOS Claude session needs a path back to your Mac — otherwise it lives only in a chat history that Claude won't remember next time.

### How Claude Projects work on iOS (the mental model)

Every chat you start **inside a Project** on iOS is linked to that Project. Claude has your `agents.md` context for the whole conversation. That chat history is stored in Claude's cloud and is accessible from any device — your Mac browser, your iPad, anywhere.

What Claude does **not** do automatically: take insights from those chats and write them back into your `agents.md`. That's a manual step — and this system makes it easy.

**Standalone chats (outside any Project) are the thing to avoid.** Claude has no context in them, and there's no way to associate them with a project later. If you're on your iPhone and tempted to start a quick chat — open a Project first.

---

### Setting up iOS Projects to match your Mac system

Do this once per Project, from a desktop browser (easiest):

1. Go to [claude.ai](https://claude.ai) and create a Project for each PARA area you have locally
2. Give it a name that matches your folder: e.g. `01-Projects`, `HelloDigital`, `Dev Lab`
3. Copy the Project UUID from the URL
4. Add it to your Mac `.env`:
   ```
   PROJECT_1_NAME=HelloDigital
   PROJECT_1_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   PROJECT_1_FOLDER=02-HelloDigital
   ```
5. Run `python3 scripts/sync.py push` on your Mac — this loads your `agents.md` into the Project
6. On iOS, open the Claude app → Projects — your Project now has context

From this point, any chat you start inside that Project on iOS has your full context.

---

### The reverse flow: getting iOS knowledge back to your Mac

There are three paths, depending on what kind of knowledge you want to preserve:

**Path 1 — Update `agents.md` from the Files app (iCloud only, tested)**

If an iOS session produced a decision, insight, or new direction that Claude should remember permanently:

1. Open **Files** app → iCloud Drive → `shared-cowork-projects` → the relevant PARA folder
2. Open `agents.md` in any text editor (Notes, iA Writer, or tap and hold → Quick Look → Edit)
3. Add the key update — a bullet, a new section, whatever fits
4. Save — iCloud syncs it to your Mac automatically within seconds
5. On your Mac, run `python3 scripts/sync.py push` to push the updated context back to Claude.ai

> If you use Dropbox or Google Drive, their iOS apps may give you access to the same files — but this is untested. For Syncthing users, there's no iOS client; use Path 3 (copy from chat) or AirDrop instead.

**Path 2 — Drop a file into `_inbox/` (iCloud tested; Dropbox/GDrive may work; Syncthing: use AirDrop)**

If you created a document, voice memo transcript, or notes file on iOS that belongs in a project:

1. From any iOS app, use the Share sheet → **Save to Files** → `_inbox/` folder (iCloud) — or the equivalent in your sync provider's iOS app
2. Or **AirDrop** it directly to your Mac if you're nearby (works regardless of sync method)
3. On your Mac: `python3 scripts/sync.py route-inbox` — routes it to the right project folder

**Path 3 — Copy key output from a chat (best for one-off insights)**

If an iOS Claude session produced something you want to keep — a plan, a list, a rewritten draft:

1. Long-press the message → Copy in the Claude iOS app
2. Open **Notes** or **Drafts** on iOS and paste it
3. Save to iCloud — it'll appear on your Mac immediately

---

### Recommended daily workflow

> The steps marked *(iCloud)* below rely on iCloud Drive being your `SYNC_METHOD`. If you use Dropbox or Google Drive, the file paths differ but the concept is the same. If you use Syncthing, substitute AirDrop for any iOS file transfers.

```
Morning (Mac)
  └─ python3 scripts/sync.py push           # push any overnight agents.md edits to Claude.ai

During the day (iPhone/iPad)
  └─ Always start chats inside a Project    # never use standalone chats
  └─ Drop files to _inbox/ via Files app    # (iCloud) for anything you want on your Mac
  └─ Or AirDrop directly to Mac             # works with any sync method

End of day / when you're back at your Mac
  └─ python3 scripts/sync.py route-inbox    # route any _inbox/ files to project folders
  └─ Open agents.md for any project that had activity today
  └─ Add 1-3 bullets of what you learned or decided
  └─ python3 scripts/sync.py push           # push updated context so tomorrow's iOS Claude knows
  └─ python3 scripts/sync.py sync-memory    # (optional) copy auto-memory to iCloud for other machines
```

The last step matters most if you use two Macs. Without it, learned preferences and feedback stay on the machine where the Cowork session happened.

The total time for the end-of-day step is usually under 2 minutes. Think of it as the equivalent of updating a shared doc after a meeting.

---

### What happens to old iOS chats?

Claude.ai stores all Project chat history in the cloud. Old chats don't disappear — you can scroll back through them in the Project on any device. But Claude doesn't automatically re-read old chats at the start of a new conversation. That's exactly what `agents.md` is for: it's your curated summary of what matters, so Claude doesn't have to re-read 50 chat threads to understand your project.

Think of `agents.md` as the living memory of a project. Old chats are the raw log. You decide what's important enough to move from the log into the memory.

---

## Claude Cowork skill

If you use [Claude Cowork](https://claude.ai), install the bundled skill so Claude can manage syncing for you:

1. Open Cowork
2. Go to **Plugins → Install from file**
3. Select `skill/cowork-ios-sync.skill`

Claude will then trigger automatically when you say things like "sync my iOS projects", "push to Claude mobile", or "why is my phone Claude out of date".

---

## Requirements

- macOS (Monterey 12+ recommended — Windows/Linux contributions welcome)
- Python 3.9+
- `pip install python-dotenv requests`
- A [Claude.ai](https://claude.ai) account with at least one Project

---

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Priority contributions:**
- Windows support (`scaffold.sh` → PowerShell equivalent)
- Linux systemd timer alternative to cron
- Dropbox / Google Drive path detection improvements
- GUI wrapper (menubar app, Raycast extension, etc.)

Please never commit `.env`, `.cookies.json`, or any personal credentials. The PR template has a security checklist.

---

## License

MIT
