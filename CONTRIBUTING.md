# Contributing to shared-cowork-projects

Thanks for helping improve this project! Here's how to get involved.

## Before you open a PR

- Check [open issues](../../issues) and [existing PRs](../../pulls) first to avoid duplicates
- For big changes, open an issue to discuss before writing code
- Keep PRs focused — one fix or feature per PR is easier to review

## What we welcome

- Bug fixes in `scripts/sync.py` or `scripts/sync_test.py`
- New sync method support (Dropbox, Google Drive, Syncthing)
- Windows or Linux support
- Improved setup scripts or error messages
- Documentation improvements
- New PARA folder template files

## What to avoid in PRs

- Hardcoded personal paths, usernames, or credentials
- Changes to `.env` itself (only `.env.template` is committed)
- Large refactors without prior discussion

## Security

**Never commit:**
- `.env` files
- `.cookies.json` or any auth tokens
- API keys or session tokens of any kind
- Personal project IDs or organization UUIDs

If you discover a security issue, please open a private [GitHub Security Advisory](../../security/advisories/new) rather than a public issue.

## How to submit a PR

1. Fork the repo
2. Create a branch: `git checkout -b fix/describe-your-change`
3. Make your changes
4. Test locally: `bash setup/scaffold.sh` in a temp folder, then `python3 scripts/sync.py push --dry-run`
5. Push and open a PR against `main`
6. Fill out the PR template — describe what changed and why

## Code style

- Python: follow PEP 8, use `pathlib.Path` (not string paths), load config from `.env` via `dotenv`
- Shell: `set -e` at the top, quote all variables, explain non-obvious steps with comments
- Commit messages: use the imperative mood (`Fix cookie setup on macOS 15`, not `Fixed...`)

## Questions?

Open a [Discussion](../../discussions) or file an issue with the `question` label.
