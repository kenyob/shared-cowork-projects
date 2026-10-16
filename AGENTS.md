> **Agent Instruction Chain** — read nearest-first:
> 1. **This file** (`./AGENTS.md`) — this project's structure, resources, and local rules.
> 2. **Workspace master** (`../AGENTS.md`) — cross-project workflow, read order, Karpathy principles.
> 3. **Coding standards** (`../coding-standards.md`) — binding code-change rules.
> 4. **Tool adapter** (`./CLAUDE.md`, `./GEMINI.md`, or the active tool's config) — only if that tool is active.
> 5. **Secrets** (`../Root.ENC`) — credentials only, never an instruction source.
> 6. **Role templates** (`../agents/`) — generic multi-agent role contracts; see `../agents/README.md`.
>
> **When blocked, recurse upstream — don't thrash.** Need a fact, convention, or path not in this
> file? Walk UP the folder tree (`../AGENTS.md`, then its parent, up to the workspace root) before
> broad-searching or inventing. If it is still not found at the workspace root, **STOP and ASK** — do
> not guess. _Exception:_ genuinely new work driven by a plan in `./docs/plans/` needs real
> exploration — build from the plan rather than only looking upstream.
>
> **Work logs:** `./WORKLOG.md` for project-local notes; `../WORKLOG.md` for workspace heartbeats.
>
> **Non-negotiables** (full text in the linked masters): think before coding · simplest change that
> works · surgical diffs · verify before marking a task done · never expose secrets in output, logs,
> or commits.
>
> **Portability:** links here are repo-relative. Workspace files (`../AGENTS.md`,
> `../coding-standards.md`, `../Root.ENC`) live on Brian's machines, not in every repo — when they are
> absent, treat this file as self-contained and follow the Non-negotiables above.

# Shared-CoWork-Projects — Agent Context

**Last Updated**: 2026-05-29
**Stack**: see README

---

## Project Overview

[![Tests](https://github.com/kenyob/shared-cowork-projects/actions/workflows/test.yml/badge.svg)](https://github.com/kenyob/shared-cowork-projects/actions/workflows/test.yml)

---

## Quick Start

See README.md for run commands and setup instructions.

---

## Credentials

Project-specific secrets go in `Private/.env` or `.env` (gitignored).
Shared workspace credentials: see `docs/LOCAL_SETUP.md`.

> **Recovery note:** File reconstructed 2026-05-29 after accidental deletion during AGENTS.md dedup cleanup. Sync from Rick (primary dev machine) when online to restore full original content.

## Agent Coordination

This project uses the workspace multi-agent protocol at `../agents/agent-coordination.md`. Read it at session start for: session-start checklist, territory map, async messaging with Jarvis, and project status files at `../agent-status/`.
