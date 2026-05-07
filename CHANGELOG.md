# Changelog

All notable changes to shared-cowork-projects will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.8.1-beta] — 2026-05-07

### Added
- `scripts/sync_test.py` — heartbeat writer and health check monitor (`--heartbeat`, `--check`, full report)
- `sync-memory` command in `sync.py` — copies Claude auto-memory files into `cowork-shared-memory/` so they travel between machines via iCloud
- `CLAUDE_MEMORY_PATH` config in `.env.template` — points to your Claude Cowork memory folder
- `tests/test_sync_memory.py` — 14 unit tests for sync-memory (dry-run, copy, manifest, edge cases)
- `tests/test_sync.py` and `tests/test_sync_test.py` — 33 unit tests total
- GitHub Actions CI (`/.github/workflows/test.yml`) — runs all tests on push and PRs across Python 3.9/3.11/3.12
- `skill/cowork-ios-sync.skill` — installable Claude Cowork skill
- iOS setup section in README covering Project setup, reverse flow, and `_inbox/` bridge
- Memory layers documentation — clearly distinguishes agents.md, auto-memory, and heartbeat logs
- iCloud-assumption caveats throughout iOS docs with "tested / untested" markers for other providers

### Changed
- README rewritten with problem-first framing and clear "what syncs / what doesn't" model
- `setup/scaffold.sh` generates template `agents.md` with prompts for each PARA folder
- `setup/install_cron.sh` reads `HEARTBEAT_CRON` from `.env` for per-machine stagger
- `.gitignore` excludes all personal project content folders and credentials

### Security
- `anthropic-client-version: "0"` header documented and tested (required to avoid 403)
- Cookie auth stores to `_skills/.cookies.json` excluded from git
- PR template includes security checklist

---

## [0.1.0] — Initial scaffolding

- PARA folder structure scaffold
- `sync.py` push to Claude.ai Projects (API key + cookie fallback)
- `.env.template` with project registry format
- MIT License
