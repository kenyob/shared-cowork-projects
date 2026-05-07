# Test Plan — shared-cowork-projects

## Running the tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Or with plain unittest (no pytest needed)
python3 -m unittest discover tests/ -v

# Run a single test file
python3 -m unittest tests.test_sync_test -v
```

Install test dependencies:
```bash
pip install pytest --break-system-packages
```

## What's covered

| File | Tests |
|---|---|
| `test_sync_test.py` | Heartbeat write, health check logic, stale detection, `.env` loading |
| `test_sync.py` | Project loading from `.env`, folder resolution, dry-run push logic |
| `test_scaffold.sh` | Shell-level integration test for scaffold.sh |

## Test philosophy

- **No network calls** — all Claude.ai API calls are mocked
- **No real cron** — heartbeat file writes are tested by inspecting output directly
- **Isolated temp dirs** — each test uses a `tempfile.TemporaryDirectory()` so nothing touches your real Cowork folder
- **Exit codes matter** — `--check` is tested for correct exit code 0/1
